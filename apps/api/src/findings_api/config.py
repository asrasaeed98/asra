from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _API_ROOT.parent.parent
_DEFAULT_DB = _API_ROOT / "findings_local.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_API_ROOT / ".env", _REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{_DEFAULT_DB}"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    anthropic_model_summary: str = "claude-haiku-4-5"
    anthropic_model_chat: str = "claude-sonnet-4-6"
    catalog_api_base: str = "https://catalog.data.gov"
    data_gov_ckan_api: str = "https://catalog.data.gov/api/3/action"
    row_cap: int = 100_000
    min_sample: int = 10_000
    sample_pct: float = 0.05
    random_seed: int = 42
    cors_origins: str = "http://localhost:3000"
    ckan_sync_max_packages: int = 40
    ckan_sync_rows: int = 25
    wb_sync_max_indicators: int = 250
    catalog_probe_enabled: bool = True
    catalog_probe_max_bytes: int = 256_000
    catalog_probe_timeout_sec: float = 20.0
    admin_sync_token: str = ""
    app_display_name: str = "Findings"
    session_data_dir: str = "./session_data"
    max_download_bytes: int = 50_000_000


settings = Settings()
