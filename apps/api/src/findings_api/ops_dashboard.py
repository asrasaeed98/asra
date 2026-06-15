"""Aggregate ops metrics for admin dashboards."""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from findings_api.models import AnalysisSession, ApiUsage, CatalogResource
from findings_api.visitor_metrics import build_visitor_metrics


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _duration_stats(durations: list[float]) -> dict[str, float | int] | None:
    if not durations:
        return None
    s = sorted(durations)
    return {
        "count": len(s),
        "mean_sec": round(statistics.mean(s), 1),
        "median_sec": round(statistics.median(s), 1),
        "p90_sec": round(_percentile(s, 90) or 0, 1),
        "max_sec": round(max(s), 1),
        "min_sec": round(min(s), 1),
    }


def build_ops_dashboard(db: Session, *, limit: int = 200, days: int = 30) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    total_sessions = db.scalar(select(func.count()).select_from(AnalysisSession)) or 0
    catalog_total = db.scalar(select(func.count()).select_from(CatalogResource)) or 0
    ingestible = (
        db.scalar(
            select(func.count())
            .select_from(CatalogResource)
            .where(CatalogResource.ingestible.is_(True))
        )
        or 0
    )

    rows = (
        db.execute(
            select(AnalysisSession).order_by(AnalysisSession.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )

    usage_rows = (
        db.execute(select(ApiUsage).order_by(ApiUsage.month.desc()).limit(6)).scalars().all()
    )

    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        daily_rows = db.execute(
            text(
                """
                SELECT DATE(created_at AT TIME ZONE 'UTC') AS day, COUNT(*) AS runs
                FROM analysis_sessions
                WHERE created_at >= :cutoff
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"cutoff": cutoff},
        ).mappings().all()
        dataset_rows = db.execute(
            text(
                """
                SELECT rid AS resource_id, COUNT(*) AS uses
                FROM analysis_sessions,
                     LATERAL jsonb_array_elements_text(resource_ids::jsonb) AS rid
                WHERE created_at >= :cutoff
                GROUP BY rid
                ORDER BY uses DESC
                LIMIT 20
                """
            ),
            {"cutoff": cutoff},
        ).mappings().all()
    else:
        window_rows = (
            db.execute(
                select(AnalysisSession.resource_ids).where(AnalysisSession.created_at >= cutoff)
            )
            .scalars()
            .all()
        )
        day_counts: Counter[str] = Counter()
        all_window = db.execute(
            select(AnalysisSession.created_at).where(AnalysisSession.created_at >= cutoff)
        ).scalars().all()
        for created in all_window:
            if created:
                day_counts[created.date().isoformat()] += 1
        daily_rows = [
            {"day": day, "runs": count}
            for day, count in sorted(day_counts.items())
        ]
        rid_counts: Counter[str] = Counter()
        for rids in window_rows:
            for rid in rids or []:
                rid_counts[str(rid)] += 1
        dataset_rows = [
            {"resource_id": rid, "uses": count}
            for rid, count in rid_counts.most_common(20)
        ]

    titles: dict[str, dict[str, str]] = {}
    if dataset_rows:
        ids = [r["resource_id"] for r in dataset_rows]
        title_rows = db.execute(
            select(CatalogResource.id, CatalogResource.title, CatalogResource.portal).where(
                CatalogResource.id.in_(ids)
            )
        ).all()
        titles = {r[0]: {"title": r[1], "portal": r[2]} for r in title_rows}

    by_status: Counter[str] = Counter()
    complete_durations: list[float] = []
    all_durations: list[float] = []
    failure_reasons: Counter[str] = Counter()
    with_intent = 0
    completed_count = 0
    two_dataset = 0
    recent_in_window = 0
    recent_sessions: list[dict] = []

    for row in rows:
        by_status[row.status] += 1
        if _as_utc(row.created_at) and _as_utc(row.created_at) >= cutoff:
            recent_in_window += 1

        resource_ids = row.resource_ids or []
        resource_count = len(resource_ids)
        if resource_count >= 2:
            two_dataset += 1
        if (row.user_intent or "").strip():
            with_intent += 1

        duration = None
        if row.created_at and row.updated_at:
            duration = (row.updated_at - row.created_at).total_seconds()
            all_durations.append(duration)
            if row.status == "complete":
                complete_durations.append(duration)
                completed_count += 1

        if row.status == "failed" and row.error:
            failure_reasons[(row.error or "")[:120]] += 1

        recent_sessions.append(
            {
                "id": row.id,
                "status": row.status,
                "phase": row.phase,
                "resource_count": resource_count,
                "resource_ids": resource_ids[:3],
                "duration_sec": round(duration, 1) if duration is not None else None,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "user_intent": ((row.user_intent or "")[:80] or None),
                "error": ((row.error or "")[:100] or None),
            }
        )

    top_datasets = []
    for r in dataset_rows:
        meta = titles.get(r["resource_id"], {})
        top_datasets.append(
            {
                "resource_id": r["resource_id"],
                "title": meta.get("title") or r["resource_id"],
                "portal": meta.get("portal") or "unknown",
                "uses": int(r["uses"]),
            }
        )

    return {
        "fetched_at": now.isoformat(),
        "visitors": build_visitor_metrics(db, days=days),
        "limitations": {
            "users": (
                "Unique visitors use an anonymous browser UUID (localStorage), not accounts."
            ),
            "time_on_app": (
                "Time on site is approximated by page views — not dwell time per page."
            ),
            "window_note": (
                f"Top datasets and daily chart use last {days} days; "
                f"recent table uses last {limit} runs."
            ),
        },
        "catalog": {"total": int(catalog_total), "ingestible": int(ingestible)},
        "sessions": {
            "total_all_time": int(total_sessions),
            "recent_window_days": days,
            "recent_in_window": recent_in_window,
            "recent_fetched": len(rows),
            "by_status": dict(by_status),
            "with_user_intent": with_intent,
            "two_dataset_runs": two_dataset,
            "completed_with_duration": completed_count,
            "duration_complete": _duration_stats(complete_durations),
            "duration_all_statuses": _duration_stats(all_durations),
        },
        "daily_runs": [{"day": str(r["day"]), "runs": int(r["runs"])} for r in daily_rows],
        "top_datasets": top_datasets,
        "failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in failure_reasons.most_common(8)
        ],
        "api_usage": [
            {
                "month": u.month,
                "tokens_in": int(u.tokens_in or 0),
                "tokens_out": int(u.tokens_out or 0),
                "cost_usd": round(float(u.cost_usd or 0), 4),
                "calls": int(u.calls or 0),
            }
            for u in usage_rows
        ],
        "recent_sessions": recent_sessions[:40],
    }
