import json
from datetime import datetime
from typing import TypedDict, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from oauth2fast_fastapi import User
from ..utils.redis_client import get_redis_client
from ..settings import settings

class UserAuthCache(TypedDict):
    id: int
    created_at: str

async def get_user_billing_info(email: str, session: AsyncSession) -> UserAuthCache:
    """
    Obtiene id y created_at del usuario, priorizando Redis.
    Si no está en Redis, consulta DB y lo guarda.
    """
    redis = get_redis_client()
    key = f"cashing:user_auth:{email}"
    
    cached_data = await redis.get(key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except json.JSONDecodeError:
            pass
            
    # Si no hay caché, buscar en DB
    result = await session.exec(select(User).where(User.email == email))
    user = result.one_or_none()
    
    if not user:
        raise ValueError(f"User with email {email} not found")
        
    info: UserAuthCache = {
        "id": user.id,
        "created_at": user.created_at.isoformat()
    }
    
    # Guardar en caché
    await redis.setex(
        key,
        settings.user_cache_ttl,
        json.dumps(info)
    )
    
    return info

async def increment_request_count(user_id: int) -> int:
    """Incrementa el contador de peticiones del usuario en Redis."""
    redis = get_redis_client()
    key = f"cashing:{user_id}:requests"
    
    # Incrementa y devuelve el nuevo valor
    return await redis.incr(key)

async def reset_request_count(user_id: int):
    """Resetea el contador de peticiones del usuario en Redis."""
    redis = get_redis_client()
    key = f"cashing:{user_id}:requests"
    await redis.set(key, 0)
