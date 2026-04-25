from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="LINKFILE_APP_ENV")
    public_base_url: str = Field(default="http://localhost:8000", alias="LINKFILE_PUBLIC_BASE_URL")
    database_url: str = Field(default="sqlite:///./linkfile.db", alias="LINKFILE_DATABASE_URL")
    jwt_secret: str = Field(default="change-me", alias="LINKFILE_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="LINKFILE_JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=1440,
        alias="LINKFILE_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:4321"],
        alias="LINKFILE_CORS_ORIGINS",
    )
    server_master_key: str = Field(default="change-me-32-bytes-key", alias="LINKFILE_SERVER_MASTER_KEY")
    default_storage_encryption_mode: str = Field(
        default="server_managed",
        alias="LINKFILE_DEFAULT_STORAGE_ENCRYPTION_MODE",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def debug(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
