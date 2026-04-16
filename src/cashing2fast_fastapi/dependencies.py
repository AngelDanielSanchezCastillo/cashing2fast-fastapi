from typing import Any
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from oauth2fast_fastapi.dependencies import get_auth_session, oauth2_dependency
from oauth2fast_fastapi.utils.token_utils import verify_token
from tools2fast_fastapi import APIResponse

from .settings import settings
from .services import billing_service
from .exceptions import PaymentRequiredException

async def require_billing_checks(
    request: Request,
    token: str = Depends(oauth2_dependency),
    session: AsyncSession = Depends(get_auth_session)
):
    """
    Dependency to check if the user has billing limits.
    """
    # 1. Decode token to get email without hitting User DB yet
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identificador",
        )
        
    # 2. Get User ID and created_at (cached in Redis)
    try:
        user_info = await billing_service.get_user_billing_info(email, session)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
        
    user_id = user_info["id"]
    created_at = datetime.fromisoformat(user_info["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    # 3. Calculate elapsed minutes
    now = datetime.now(timezone.utc)
    elapsed_minutes = (now - created_at).total_seconds() / 60
    
    # 4. Evaluate phases
    
    # Phase 1: Unlimited (Free period)
    if elapsed_minutes <= settings.free_minutes:
        return True
        
    # Phase 2: Tracked (Redirect period)
    if elapsed_minutes <= (settings.free_minutes + settings.redirect_minutes):
        count = await billing_service.increment_request_count(user_id)
        if count > settings.max_requests:
            # Reseteo el valor en el redis para que la pueda seguir ocupando 
            # hasta llegar a ese número nuevamente después de la redirección
            await billing_service.reset_request_count(user_id)
            # Raise exception to stop execution and return 402
            raise PaymentRequiredException(
                message="Límite de peticiones alcanzado. Por favor, realiza un pago."
            )
        return True
        
    # Phase 3: Blocked (Expired)
    raise PaymentRequiredException(
        message="Su periodo de uso ha expirado. Por favor, realice un pago para continuar."
    )

def register_billing_exception_handler(app: Any):
    """
    Register the global exception handler for PaymentRequiredException.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse
    
    @app.exception_handler(PaymentRequiredException)
    async def billing_exception_handler(request: Request, exc: PaymentRequiredException):
        return APIResponse.payment_required(
            message=exc.message,
            error=exc.error
        )
