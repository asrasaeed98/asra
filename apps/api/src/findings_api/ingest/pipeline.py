"""Download catalog files and load into per-session DuckDB."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from findings_api.config import settings
from findings_api.ingest.download import DownloadError, fetch_resource_bytes
from findings_api.ingest.duckdb_store import (
    build_analysis_view_sql,
    connect,
    session_db_path,
    validate_filter,
)
from findings_api.licensing import is_allowed
from findings_api.models import AnalysisSession, CatalogResource
from findings_api.sampling import compute_analysis_n, sampling_tier

logger = logging.getLogger(__name__)


def _set_progress(
    db: Session,
    session: AnalysisSession,
    *,
    phase: str,
    message: str,
    percent: int,
    status: str | None = None,
) -> None:
    session.phase = phase
    session.message = message
    session.percent = percent
    if status:
        session.status = status
    db.add(session)
    db.commit()


def _profile_table(conn, table: str) -> dict:
    total = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    cols = conn.execute(f"DESCRIBE {table}").fetchall()
    columns = [{"name": row[0], "type": row[1]} for row in cols]
    sample_rows = conn.execute(f"SELECT * FROM {table} LIMIT 5").fetchdf().to_dict(orient="records")
    return {
        "table": table,
        "row_count": total,
        "columns": columns,
        "sample_rows": sample_rows,
    }


def _load_bytes(conn, table: str, data: bytes, kind: str, portal: str) -> None:
    if kind == "json" or portal == "world_bank":
        _load_json(conn, table, data)
        return
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        conn.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, sample_size=20000)",
            [tmp_path],
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _load_json(conn, table: str, data: bytes) -> None:
    payload = json.loads(data.decode("utf-8", errors="replace"))
    rows: list[dict]
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
        rows = payload[1]
    elif isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise DownloadError("Unsupported JSON shape")
    if not rows:
        conn.execute(f"CREATE OR REPLACE TABLE {table} (placeholder VARCHAR)")
        return
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tmp:
        json.dump(rows, tmp)
        tmp_path = tmp.name
    try:
        conn.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_json_auto(?)",
            [tmp_path],
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _common_join_columns(profiles: list[dict]) -> list[str]:
    if len(profiles) < 2:
        return []
    names_sets = []
    for p in profiles:
        names_sets.append({c["name"].lower(): c["name"] for c in p["columns"]})
    shared = set(names_sets[0])
    for ns in names_sets[1:]:
        shared &= set(ns)
    preferred = ["countryiso3code", "country", "state", "state_code", "year", "date", "id"]
    ordered = []
    for key in preferred:
        if key in shared:
            ordered.append(names_sets[0][key])
    for key in sorted(shared):
        canon = names_sets[0][key]
        if canon not in ordered:
            ordered.append(canon)
    return ordered[:12]


async def run_ingest(db: Session, session_id: str) -> None:
    session = db.get(AnalysisSession, session_id)
    if not session:
        return

    try:
        _set_progress(db, session, phase="ingest", message="Loading your data", percent=5, status="ingesting")
        resources: list[CatalogResource] = []
        for rid in session.resource_ids:
            row = db.get(CatalogResource, rid)
            if not row:
                raise DownloadError(f"Unknown catalog resource: {rid}")
            if not is_allowed(row.license_normalized, row.portal):
                raise DownloadError(f"License not allowed for ingest: {rid}")
            if not row.resource_url:
                raise DownloadError(f"No download URL for {rid}")
            resources.append(row)

        session_db_path(session_id).unlink(missing_ok=True)
        conn = connect(session_id)
        profiles: list[dict] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for idx, resource in enumerate(resources):
                pct = 10 + int(70 * (idx / max(len(resources), 1)))
                _set_progress(
                    db,
                    session,
                    phase="ingest",
                    message=f"Downloading {resource.title[:60]}…",
                    percent=pct,
                )
                data, kind = await fetch_resource_bytes(resource.resource_url, client=client)
                raw_table = f"raw_{idx}"
                _load_bytes(conn, raw_table, data, kind, resource.portal)
                config = session.config or {}
                filters = config.get("filters") or {}
                filter_sql = filters.get(str(idx)) or filters.get(raw_table)
                if filter_sql and not validate_filter(filter_sql):
                    raise DownloadError("Invalid filter expression")
                profile = _profile_table(conn, raw_table)
                profile["resource_id"] = resource.id
                profile["title"] = resource.title
                profile["raw_table"] = raw_table
                profiles.append(profile)

        config = dict(session.config or {})
        config.setdefault("ml_enabled", True)
        config.setdefault("filters", {})
        session.config = config
        session.duckdb_path = str(session_db_path(session_id))
        session.row_counts = {str(i): p["row_count"] for i, p in enumerate(profiles)}
        session.preview = {
            "datasets": profiles,
            "suggested_join_keys": _common_join_columns(profiles),
            "sampling_tier": sampling_tier(max(session.row_counts.values(), default=0)),
        }
        apply_session_config(db, session_id)
        session = db.get(AnalysisSession, session_id)
        if session:
            _set_progress(
                db,
                session,
                phase="ready",
                message="Data loaded — review filters and sample size",
                percent=100,
                status="ready",
            )
        conn.close()
    except Exception as exc:
        logger.exception("Ingest failed for %s", session_id)
        session = db.get(AnalysisSession, session_id)
        if session:
            session.status = "failed"
            session.phase = "failed"
            session.message = str(exc)
            session.error = str(exc)
            session.percent = 0
            db.add(session)
            db.commit()


def apply_session_config(db: Session, session_id: str) -> None:
    session = db.get(AnalysisSession, session_id)
    if not session or not session.duckdb_path:
        return
    preview = session.preview or {}
    datasets = preview.get("datasets") or []
    if not datasets:
        return

    config = session.config or {}
    filters = config.get("filters") or {}
    conn = connect(session_id)
    analysis_counts: dict[str, int] = {}

    for idx, item in enumerate(datasets):
        raw_table = item["raw_table"]
        total = int(item["row_count"])
        filter_sql = filters.get(str(idx)) or filters.get(raw_table) or ""
        if filter_sql and not validate_filter(filter_sql):
            raise ValueError("Invalid filter expression")
        filtered_total = total
        if filter_sql.strip():
            filtered_total = int(
                conn.execute(f"SELECT COUNT(*) FROM {raw_table} WHERE {filter_sql.strip()}").fetchone()[0]
            )
        analysis_n = compute_analysis_n(filtered_total)
        analysis_table = f"analysis_{idx}"
        sql = build_analysis_view_sql(
            raw_table,
            analysis_table,
            filter_sql=filter_sql or None,
            total_rows=filtered_total,
            analysis_n=analysis_n,
            seed=settings.random_seed,
        )
        conn.execute(sql)
        analysis_counts[str(idx)] = int(conn.execute(f"SELECT COUNT(*) FROM {analysis_table}").fetchone()[0])
        item["analysis_table"] = analysis_table
        item["analysis_n"] = analysis_counts[str(idx)]
        item["filtered_row_count"] = filtered_total

    preview["analysis_row_counts"] = analysis_counts
    session.preview = preview
    session.row_counts = analysis_counts
    db.add(session)
    db.commit()
    conn.close()
