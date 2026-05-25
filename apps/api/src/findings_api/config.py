from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://findings:findings@localhost:5432/findings"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    anthropic_model_summary: str = "claude-haiku-4-5"
    anthropic_model_chat: str = "claude-sonnet-4-6"
    data_gov_ckan_api: str = "https://catalog.data.gov/api/3/action"
    row_cap: int = 100_000
    min_sample: int = 10_000
    sample_pct: float = 0.05
    random_seed: int = 42
    cors_origins: str = "http://localhost:3000"


settings = Settings()
