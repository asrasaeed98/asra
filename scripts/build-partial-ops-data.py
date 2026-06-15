#!/usr/bin/env python3
"""Build ops dashboard JSON from prod /admin/runs/snapshot when /admin/ops/dashboard is unavailable."""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

ET = ZoneInfo("America/New_York")

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def percentile(sorted_vals: list[float], p: float) -> float | None:
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


def to_et_fields(iso: str | None) -> tuple[str, str]:
    if not iso:
        return "", ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    et = dt.astimezone(ET)
    return et.strftime("%Y-%m-%d"), et.strftime("%Y-%m-%d %H:%M")


def duration_stats(durations: list[float]) -> dict | None:
    if not durations:
        return None
    s = sorted(durations)
    return {
        "count": len(s),
        "mean_sec": round(statistics.mean(s), 1),
        "median_sec": round(statistics.median(s), 1),
        "p90_sec": round(percentile(s, 90) or 0, 1),
        "max_sec": round(max(s), 1),
        "min_sec": round(min(s), 1),
    }


def main() -> int:
    api = os.environ.get("API_URL", "https://asra-production.up.railway.app").rstrip("/")
    token = os.environ.get("ADMIN_SYNC_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    limit = int(os.environ.get("LIMIT", "200"))

    with httpx.Client(timeout=30.0) as client:
        health = client.get(f"{api}/health").json()
        dash = client.get(
            f"{api}/admin/ops/dashboard?limit={limit}&days=30",
            headers=headers,
        )
        if dash.is_success:
            print(json.dumps(dash.json()))
            return 0

        snap = client.get(
            f"{api}/admin/runs/snapshot?limit={min(limit, 200)}",
            headers=headers,
        )
        snap.raise_for_status()
        snap = snap.json()

    complete_durations: list[float] = []
    all_durations: list[float] = []
    by_status: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    daily: Counter[str] = Counter()
    two_dataset = 0
    all_sessions: list[dict] = []

    for session in snap["sessions"]:
        by_status[session["status"]] += 1
        day, created_display = to_et_fields(session.get("created_at"))
        if day:
            daily[day] += 1
        duration = session.get("duration_sec")
        if duration is not None:
            all_durations.append(duration)
            if session["status"] == "complete":
                complete_durations.append(duration)
        if session.get("error"):
            failures[(session["error"] or "")[:120]] += 1
        resource_count = session.get("resource_count") or 0
        if resource_count >= 2:
            two_dataset += 1
        all_sessions.append(
            {
                "id": session["id"][:8],
                "status": session["status"],
                "resource_count": resource_count,
                "duration_sec": round(duration, 1) if duration is not None else None,
                "day": day,
                "created_at": created_display,
                "error": ((session.get("error") or "")[:120] or None),
            }
        )

    out = {
        "fetched_at": snap.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
        "source": "prod /admin/runs/snapshot (deploy API for top datasets)",
        "limitations": {
            "users": "No per-visitor identity — counts are analysis runs, not unique people.",
            "time_on_app": (
                "Browser session time is not tracked — only server pipeline duration "
                "(created→updated)."
            ),
            "window_note": f"Based on last {len(snap['sessions'])} analysis runs. Ask in chat to refresh.",
        },
        "catalog": {"total": health.get("catalog_count", 0), "ingestible": None},
        "sessions": {
            "total_all_time": None,
            "recent_fetched": len(snap["sessions"]),
            "by_status": dict(by_status),
            "two_dataset_runs": two_dataset,
            "completed_with_duration": len(complete_durations),
            "duration_complete": duration_stats(complete_durations),
            "duration_all_statuses": duration_stats(all_durations),
        },
        "daily_runs": [{"day": day, "runs": count} for day, count in sorted(daily.items())],
        "failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in failures.most_common(6)
        ],
        "api_usage": snap.get("api_usage", []),
        "visitors": {
            "tracking_since": None,
            "total_page_views": 0,
            "unique_visitors_all_time": 0,
            "window_days": 30,
            "page_views_in_window": 0,
            "unique_visitors_in_window": 0,
            "unique_visitors_with_analysis": 0,
            "daily_unique_visitors": [],
            "top_paths": [],
            "note": "Deploy web+API update to start visitor tracking.",
        },
        "all_sessions": all_sessions,
        "date_bounds": {
            "min": min((s["day"] for s in all_sessions if s["day"]), default=""),
            "max": max((s["day"] for s in all_sessions if s["day"]), default=""),
            "timezone": "America/New_York",
        },
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
