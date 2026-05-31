from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/store_intelligence"

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_async_scheme(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v
    redis_url: str = "redis://localhost:6379/0"
    clips_dir: str = "/data/clips"
    output_dir: str = "/data/events"
    store_layout_path: str = "/data/store_layout.json"
    pos_transactions_path: str = "/data/pos_transactions.csv"
    model_path: str = "/models"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = int(os.environ.get("PORT", "8000"))


settings = Settings()
