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

    cors_origins_str: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_str.split(",") if o.strip()]

    redis_url: str = "redis://localhost:6379/0"

    @property
    def redis_kwargs(self) -> dict:
        """Return Redis connection kwargs, auto-enabling TLS for Upstash."""
        return {"url": self.redis_url, "ssl": "upstash" in self.redis_url, "decode_responses": True}

    clips_dir: str = "/data/clips"
    output_dir: str = "/data/events"
    store_layout_path: str = "/data/store_layout.json"
    pos_transactions_path: str = "/data/pos_transactions.csv"
    model_path: str = "/models"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = int(os.environ.get("PORT", "8000"))


settings = Settings()
