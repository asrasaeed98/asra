"""Aggregate anonymous visitor metrics for ops dashboards."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from findings_api.models import AnalysisSession, AppVisit

ET = ZoneInfo("America/New_York")


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _et_day(dt: datetime) -> str:
    return _as_utc(dt).astimezone(ET).strftime("%Y-%m-%d")


def build_visitor_metrics(db: Session, *, days: int = 30) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    dialect = db.get_bind().dialect.name

    total_visits = db.scalar(select(func.count()).select_from(AppVisit)) or 0
    if total_visits == 0:
        return {
            "tracking_since": None,
            "total_page_views": 0,
            "unique_visitors_all_time": 0,
            "window_days": days,
            "page_views_in_window": 0,
            "unique_visitors_in_window": 0,
            "unique_visitors_with_analysis": 0,
            "daily_unique_visitors": [],
            "top_paths": [],
            "note": (
                "Visitor tracking starts after web+API deploy. "
                "Each browser gets an anonymous UUID in localStorage."
            ),
        }

    tracking_since_row = db.scalar(select(func.min(AppVisit.created_at)))
    unique_all_time = (
        db.scalar(select(func.count(func.distinct(AppVisit.visitor_id))).select_from(AppVisit))
        or 0
    )

    if dialect == "postgresql":
        window_visits = int(
            db.scalar(
                select(func.count())
                .select_from(AppVisit)
                .where(AppVisit.created_at >= cutoff)
            )
            or 0
        )
        unique_in_window = int(
            db.scalar(
                select(func.count(func.distinct(AppVisit.visitor_id)))
                .select_from(AppVisit)
                .where(AppVisit.created_at >= cutoff)
            )
            or 0
        )
        unique_with_analysis = int(
            db.scalar(
                select(func.count(func.distinct(AnalysisSession.visitor_id)))
                .select_from(AnalysisSession)
                .where(
                    AnalysisSession.visitor_id.is_not(None),
                    AnalysisSession.created_at >= cutoff,
                )
            )
            or 0
        )
        daily_rows = db.execute(
            text(
                """
                SELECT DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York') AS day,
                       COUNT(DISTINCT visitor_id) AS visitors,
                       COUNT(*) AS page_views
                FROM app_visits
                WHERE created_at >= :cutoff
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"cutoff": cutoff},
        ).mappings().all()
        path_rows = db.execute(
            text(
                """
                SELECT path, COUNT(*) AS views, COUNT(DISTINCT visitor_id) AS visitors
                FROM app_visits
                WHERE created_at >= :cutoff
                GROUP BY path
                ORDER BY views DESC
                LIMIT 10
                """
            ),
            {"cutoff": cutoff},
        ).mappings().all()
    else:
        visits = (
            db.execute(select(AppVisit).where(AppVisit.created_at >= cutoff)).scalars().all()
        )
        window_visits = len(visits)
        unique_in_window = len({v.visitor_id for v in visits})
        session_visitors = (
            db.execute(
                select(AnalysisSession.visitor_id)
                .where(
                    AnalysisSession.visitor_id.is_not(None),
                    AnalysisSession.created_at >= cutoff,
                )
            )
            .scalars()
            .all()
        )
        unique_with_analysis = len({v for v in session_visitors if v})
        day_unique: dict[str, set[str]] = {}
        day_page_views: Counter[str] = Counter()
        path_views: Counter[str] = Counter()
        path_unique: dict[str, set[str]] = {}
        for visit in visits:
            created = _as_utc(visit.created_at)
            if not created:
                continue
            day = _et_day(created)
            day_page_views[day] += 1
            day_unique.setdefault(day, set()).add(visit.visitor_id)
            path_views[visit.path] += 1
            path_unique.setdefault(visit.path, set()).add(visit.visitor_id)
        daily_rows = [
            {"day": day, "visitors": len(day_unique[day]), "page_views": day_page_views[day]}
            for day in sorted(day_unique)
        ]
        path_rows = [
            {
                "path": path,
                "views": views,
                "visitors": len(path_unique.get(path, set())),
            }
            for path, views in path_views.most_common(10)
        ]

    return {
        "tracking_since": tracking_since_row.isoformat() if tracking_since_row else None,
        "total_page_views": int(total_visits),
        "unique_visitors_all_time": int(unique_all_time),
        "window_days": days,
        "page_views_in_window": int(window_visits),
        "unique_visitors_in_window": int(unique_in_window),
        "unique_visitors_with_analysis": int(unique_with_analysis),
        "daily_unique_visitors": [
            {
                "day": str(r["day"]),
                "visitors": int(r["visitors"]),
                "page_views": int(r["page_views"]),
            }
            for r in daily_rows
        ],
        "top_paths": [
            {
                "path": r["path"],
                "views": int(r["views"]),
                "visitors": int(r["visitors"]),
            }
            for r in path_rows
        ],
        "note": (
            "Anonymous browser UUID (localStorage). Same person on two devices counts as two."
        ),
    }
