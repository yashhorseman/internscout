"""Settings come from environment variables, or from .env on a laptop."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/internscout"
    gemini_api_key: str = ""
    user_agent: str = "InternScout/0.1"
    chat_model: str = "gemini-3.5-flash-lite"
    daily_token_budget: int = 1_000_000  # chosen, not a provider limit; above it, search only
    rate_limit_messages: int = 20        # per session and per address ...
    rate_limit_seconds: int = 600        # ... in this many seconds
    admin_token: str = ""                # empty: /admin/stats is switched off
    mark_sessions_as_test: bool = False  # set on your own machine; excluded from statistics


settings = Settings()
