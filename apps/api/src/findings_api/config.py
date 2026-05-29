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
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3002,http://127.0.0.1:3002"
    )
    ckan_sync_max_packages: int = 200
    ckan_sync_max_indexed: int = 0
    ckan_sync_rows: int = 100
    ckan_sync_max_pages: int = 20
    wb_sync_max_indicators: int = 2000
    wb_sync_max_indexed: int = 0
    wb_sync_max_per_family: int = 2
    wb_sync_max_per_topic: int = 250
    catalog_probe_enabled: bool = True
    catalog_probe_max_bytes: int = 256_000
    catalog_probe_timeout_sec: float = 20.0
    catalog_min_rows: int = 20
    analysis_min_rows: int = 20
    fred_api_key: str = ""
    fred_sync_max_series: int = 150
    fred_sync_max_indexed: int = 0
    catalog_sync_interval_hours: float = 0
    catalog_sync_run_on_startup: bool = False
    catalog_probe_interval_hours: float = 0
    catalog_probe_batch_size: int = 500
    admin_sync_token: str = ""
    app_display_name: str = "Findings"
    session_data_dir: str = "./session_data"
    max_download_bytes: int = 50_000_000
    download_max_retries: int = 3
    download_backoff_base_sec: float = 0.5
    chat_max_questions: int = 5
    chat_max_tokens: int = 400
    chat_history_turns: int = 4
    chat_max_message_chars: int = 1000
    chat_context_char_cap: int = 16000
    # Hard ceiling on Anthropic spend per calendar month (USD). <= 0 disables the cap.
    ai_monthly_budget_usd: float = 100.0


settings = Settings()
