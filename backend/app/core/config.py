from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "change-me"
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings loaded from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Mis Eventos"
    database_url: str = "postgresql+psycopg://mis_eventos:mis_eventos@localhost:5432/mis_eventos"
    jwt_secret: str = INSECURE_DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    redis_url: str | None = None
    cache_ttl_events_seconds: int = Field(default=60, gt=0)
    cache_ttl_sessions_seconds: int = Field(default=120, gt=0)
    cache_ttl_speakers_seconds: int = Field(default=300, gt=0)

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_strong(cls, value: str) -> str:
        if value == INSECURE_DEFAULT_SECRET or len(value) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET must be set to a random value of at least {MIN_JWT_SECRET_LENGTH} "
                f"characters (the placeholder '{INSECURE_DEFAULT_SECRET}' is not accepted). "
                "Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
