from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCOUT_", env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/scout.db"
    release_root: Path = Path("data/releases")
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    allow_synthetic: bool = True
    ollama_enabled: bool = False
    ollama_model: str = "qwen2.5:3b"
    api_football_key: str = ""
    pitchapi_key: SecretStr = SecretStr("")
    storage_account: str = ""
    request_limit: int = 90
    serve_private_evidence: bool = False
