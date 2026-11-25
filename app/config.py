"""Settings come from environment variables, or from .env on a laptop."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/internscout"
    gemini_api_key: str = ""
    user_agent: str = "InternScout/0.1"


settings = Settings()
