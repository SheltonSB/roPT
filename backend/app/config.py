"""
config.py
What this file does:
- Uses pydantic-settings (BaseSettings) to load env vars + .env automatically.
- Keeps deployment portable: local -> docker -> cloud.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_host: str = Field(default="0.0.0.0", alias="ROPT_BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="ROPT_BACKEND_PORT")

    mongo_uri: str = Field(default="mongodb://127.0.0.1:27017", alias="ROPT_MONGO_URI")
    mongo_db: str = Field(default="ropt", alias="ROPT_MONGO_DB")
    mongo_min_pool_size: int = Field(default=0, alias="ROPT_MONGO_MIN_POOL_SIZE")
    mongo_max_pool_size: int = Field(default=100, alias="ROPT_MONGO_MAX_POOL_SIZE")

    events_ttl_days: int = Field(default=0, alias="ROPT_EVENTS_TTL_DAYS")
    metrics_ttl_days: int = Field(default=7, alias="ROPT_METRICS_TTL_DAYS")

    cuopt_base_url: str = Field(default="http://127.0.0.1:5000", alias="ROPT_CUOPT_URL")
    cuopt_timeout_s: float = Field(default=0.05, alias="ROPT_CUOPT_TIMEOUT_S")

    event_queue_max: int = Field(default=20000, alias="ROPT_EVENT_QUEUE_MAX")
    max_events: int = Field(default=5000, alias="ROPT_MAX_EVENTS")

    cors_allow_origins: str = Field(default="*", alias="ROPT_CORS_ALLOW_ORIGINS")
    edge_api_key: str | None = Field(default=None, alias="ROPT_EDGE_API_KEY")
    dashboard_api_key: str | None = Field(default=None, alias="ROPT_DASHBOARD_API_KEY")
    redis_url: str | None = Field(default=None, alias="ROPT_REDIS_URL")
    workers: int = Field(default=2, alias="ROPT_WORKERS")


settings = Settings()
