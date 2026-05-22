from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # postgresql+psycopg:// uses psycopg v3 (Python 3.13 compatible)
    # Port 9876 is the local PostgreSQL 17 instance (non-standard port set during install)
    database_url: str = "postgresql+psycopg://bomatic:bomatic@localhost:9876/bomatic"
    anthropic_api_key: str = ""
    upload_dir: str = "storage"
    bomatic_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


CLAUDE_MODEL = "claude-sonnet-4-6"
