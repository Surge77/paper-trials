from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAPERTRIALS_", env_file=".env", extra="ignore")

    db_path: Path = Path("papertrials.db")
    ollama_url: str = "http://127.0.0.1:11434"
    gemma_model: str = "gemma3:4b"
    gemma_timeout_s: float = 60.0
    # Set to false to always use the simple baseline model (useful on very slow machines).
    use_tabpfn: bool = True
    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
