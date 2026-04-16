import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from cashing2fast_fastapi import require_billing_checks, settings
from cashing2fast_fastapi.dependencies import register_billing_exception_handler

# Mock app
app = FastAPI()
register_billing_exception_handler(app)

@app.get("/test")
async def test_route(dep = Depends(require_billing_checks)):
    return {"message": "success"}

@pytest.fixture
def mock_redis():
    with patch("cashing2fast_fastapi.services.billing_service.get_redis_client") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_verify_token():
    with patch("cashing2fast_fastapi.dependencies.verify_token") as mock:
        yield mock

@pytest.mark.asyncio
async def test_phase_1_free(mock_redis, mock_verify_token):
    """Phase 1: User created recently, should allow without counting."""
    mock_verify_token.return_value = {"sub": "test@example.com"}
    
    # Mock user info in Redis (Phase 1: now - 5 mins)
    created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    mock_redis.get.return_value = '{"id": 1, "created_at": "' + created_at.isoformat() + '"}'
    
    # Settings: free=10, redirect=60
    with patch.object(settings, "free_minutes", 10):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/test", headers={"Authorization": "Bearer token"})
            
    assert response.status_code == 200
    assert response.json() == {"message": "success"}
    # Should NOT increment count in phase 1
    mock_redis.incr.assert_not_called()

@pytest.mark.asyncio
async def test_phase_2_tracked_ok(mock_redis, mock_verify_token):
    """Phase 2: User in tracking period, should count and allow if below max."""
    mock_verify_token.return_value = {"sub": "test@example.com"}
    
    # Mock user info in Redis (Phase 2: now - 20 mins, where free=10)
    created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    mock_redis.get.return_value = '{"id": 1, "created_at": "' + created_at.isoformat() + '"}'
    # Current count = 1
    mock_redis.incr.return_value = 1
    
    with patch.object(settings, "free_minutes", 10):
        with patch.object(settings, "redirect_minutes", 60):
            with patch.object(settings, "max_requests", 5):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    response = await ac.get("/test", headers={"Authorization": "Bearer token"})
            
    assert response.status_code == 200
    mock_redis.incr.assert_called_once_with("cashing:1:requests")

@pytest.mark.asyncio
async def test_phase_2_tracked_limit_reached(mock_redis, mock_verify_token):
    """Phase 2: User reached limit, should return 402 and reset."""
    mock_verify_token.return_value = {"sub": "test@example.com"}
    
    created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    mock_redis.get.return_value = '{"id": 1, "created_at": "' + created_at.isoformat() + '"}'
    # Current count = 6 (limit is 5)
    mock_redis.incr.return_value = 6
    
    with patch.object(settings, "free_minutes", 10):
        with patch.object(settings, "redirect_minutes", 60):
            with patch.object(settings, "max_requests", 5):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    response = await ac.get("/test", headers={"Authorization": "Bearer token"})
            
    assert response.status_code == 402
    assert response.json()["message"] == "Límite de peticiones alcanzado. Por favor, realiza un pago."
    # Should reset count
    mock_redis.set.assert_called_with("cashing:1:requests", 0)

@pytest.mark.asyncio
async def test_phase_3_expired(mock_redis, mock_verify_token):
    """Phase 3: Period expired, should block always."""
    mock_verify_token.return_value = {"sub": "test@example.com"}
    
    # Phase 3: now - 100 mins (free=10 + redirect=60 = 70 mins total period)
    created_at = datetime.now(timezone.utc) - timedelta(minutes=100)
    mock_redis.get.return_value = '{"id": 1, "created_at": "' + created_at.isoformat() + '"}'
    
    with patch.object(settings, "free_minutes", 10):
        with patch.object(settings, "redirect_minutes", 60):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/test", headers={"Authorization": "Bearer token"})
            
    assert response.status_code == 402
    assert "expirado" in response.json()["message"]
