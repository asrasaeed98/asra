from pathlib import Path

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        return value

    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    anthropic_model_summary: str = "claude-haiku-4-5"
    anthropic_model_chat: str = "claude-sonnet-4-6"
    anthropic_model_measure: str = "claude-haiku-4-5"
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
    nyc_open_data_base: str = "https://data.cityofnewyork.us"
    # Optional Socrata app token. Not required for public datasets, but raises
    # the anonymous rate limit. Sent as the X-App-Token header when set.
    socrata_app_token: str = ""
    nyc_sync_max_ingestible: int = 20
    nyc_sync_max_indexed: int = 0
    catalog_sync_interval_hours: float = 0
    catalog_sync_run_on_startup: bool = False
    catalog_sync_prune_enabled: bool = False
    catalog_probe_interval_hours: float = 0
    catalog_probe_batch_size: int = 500
    admin_sync_token: str = ""
    app_display_name: str = "Findings"
    session_data_dir: str = "./session_data"
    max_download_bytes: int = 100_000_000
    download_max_retries: int = 3
    download_backoff_base_sec: float = 0.5
    download_chunk_timeout_sec: float = 180.0
    download_large_timeout_sec: float = 300.0
    socrata_download_chunk_rows: int = 10_000
    # Max concurrent chunk requests per Socrata dataset. The SODA2 public API
    # is generous; 5 concurrent requests cuts the 10-serial-chunk wall time ~5x
    # without triggering rate limits on unauthenticated calls.
    socrata_concurrent_chunks: int = 5
    download_large_row_hint: int = 50_000
    # World Bank page size — start large; fall back 20k → 10k → 5k → 1k on 502/timeout.
    wb_download_per_page: int = 20000
    wb_download_max_retries: int = 5
    wb_download_backoff_base_sec: float = 1.0
    chat_max_questions: int = 5
    chat_max_tokens: int = 400
    chat_history_turns: int = 4
    chat_max_message_chars: int = 1000
    chat_context_char_cap: int = 16000
    chat_query_max_rows: int = 25
    chat_max_query_rounds: int = 1
    # Hard ceiling on Anthropic spend per calendar month (USD). <= 0 disables the cap.
    ai_monthly_budget_usd: float = 100.0


settings = Settings()
