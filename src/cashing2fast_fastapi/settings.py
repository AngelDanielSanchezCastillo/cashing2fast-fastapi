"""
Cashing2Fast FastAPI Settings

Configuration for cashing2fast-fastapi module using pydantic-settings.
Reads from environment variables with CASHING_ prefix.
"""

import os
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Look for .env in the current working directory (where the app is running)
DOTENV_PATH = os.path.join(os.getcwd(), ".env")

class RedisSettings(BaseModel):
    """Redis configuration for caching billing info."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None
    decode_responses: bool = True

class Settings(BaseSettings):
    """Billing and request limit configuration settings."""

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        env_prefix="CASHING_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Redis settings
    redis: RedisSettings = RedisSettings()

    # Feature flags
    redis_enabled: bool = True

    # Billing Logic Limits
    # Period where users are never penalized/redirected (in minutes)
    free_minutes: int = 0
    # Period following the free minutes where users are tracked (in minutes)
    redirect_minutes: int = 60
    # Number of allowed requests during the redirect_minutes phase
    max_requests: int = 100

    # Cache settings
    # Default TTL for cached user info (created_at)
    user_cache_ttl: int = 86400  # 24 hours

try:
    settings = Settings()
except Exception as e:
    # Use log2fast_fastapi for proper error logging if available
    try:
        from log2fast_fastapi import get_logger
        logger = get_logger(__name__)
        logger.exception(
            "🚨 Error loading Cashing2Fast configuration",
            extra_data={
                "error": str(e),
                "dotenv_path": DOTENV_PATH,
            },
        )
    except ImportError:
        print(f"🚨 Error loading Cashing2Fast configuration: {e}")
    raise
