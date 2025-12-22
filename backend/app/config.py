#author Shelton Bumhe and Defi Kapaba 

from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_host: str = Field(default="0.0.0.0", alias="ROPT_BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="ROPT_BACKEND_PORT")

    cuopt_base_url: str = Field(default="http://127.0.0.1:5000", alias="ROPT_CUOPT_URL")
    cuopt_timeout_s: float = Field(default=0.05, alias="ROPT_CUOPT_TIMEOUT_S")

    event_queue_max: int = Field(default=20000, alias="ROPT_EVENT_QUEUE_MAX")
    max_events: int = Field(default=5000, alias="ROPT_MAX_EVENTS")

