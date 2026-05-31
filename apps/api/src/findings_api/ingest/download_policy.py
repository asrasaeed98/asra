"""Download size policy and user-facing ingest messages."""

from __future__ import annotations

from findings_api.config import settings
from findings_api.models import CatalogResource


def max_download_mb() -> int:
    return settings.max_download_bytes // 1_000_000


def is_large_download(*, portal: str, row_count_hint: int | None) -> bool:
    hint = row_count_hint or 0
    if portal == "nyc_open_data" and hint >= settings.download_large_row_hint:
        return True
    return hint >= settings.row_cap


def large_download_start_message(
    *,
    title: str,
    row_count_hint: int | None,
    portal: str = "",
) -> str:
    cap_mb = max_download_mb()
    row_cap = settings.row_cap
    rows = row_count_hint
    if rows and rows > row_cap:
        size_note = f"up to {row_cap:,} rows sampled from {rows:,}"
    elif rows:
        size_note = f"~{rows:,} rows"
    else:
        size_note = f"up to {row_cap:,} rows"
    portal_note = "NYC Open Data" if portal == "nyc_open_data" else "dataset"
    return (
        f"Downloading {title} ({size_note}) — large {portal_note} downloads can take "
        f"2–5 minutes (up to {cap_mb}MB). Please keep this page open."
    )


def download_progress_message(*, rows_done: int, row_target: int) -> str:
    pct = min(99, int(100 * rows_done / max(row_target, 1)))
    return f"Downloaded {rows_done:,} of up to {row_target:,} rows ({pct}%)…"


def download_complete_message(*, title: str, rows: int, size_bytes: int) -> str:
    size_mb = size_bytes / 1_000_000
    return f"Loaded {title} — {rows:,} rows ({size_mb:.1f}MB). Processing…"


def resource_is_large(resource: CatalogResource) -> bool:
    return is_large_download(portal=resource.portal, row_count_hint=resource.row_count_hint)
