from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ZoneMonitoring"
    PROJECT_NAME: str = "Zone Monitoring"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list)
    SECRET_KEY: str = "CHANGE_ME"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://zone_user:Ural196User!@localhost:5432/zone_monitoring",
        description="SQLAlchemy-style database URL",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
