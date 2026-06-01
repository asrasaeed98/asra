#!/usr/bin/env bash
# Fetch prod analysis runs snapshot as JSON (for Cursor Canvas refresh).
# Prefers live API; falls back to direct Postgres when Railway CLI is linked.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-https://asra-production.up.railway.app}"
LIMIT="${LIMIT:-50}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -n "${ADMIN_SYNC_TOKEN:-}" ]]; then
  if curl -sf "${API_URL}/admin/runs/snapshot?limit=${LIMIT}" \
    -H "Authorization: Bearer ${ADMIN_SYNC_TOKEN}" 2>/dev/null; then
    exit 0
  fi
fi

PY="${ROOT}/apps/api/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo '{"error":"No snapshot: API endpoint unavailable and apps/api/.venv missing"}' >&2
  exit 1
fi

DB_PUBLIC="${DATABASE_PUBLIC_URL:-}"
if [[ -z "$DB_PUBLIC" ]]; then
  DB_PUBLIC="$(npx railway variable list --service Postgres -k 2>/dev/null \
    | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2- || true)"
fi
if [[ -z "$DB_PUBLIC" ]]; then
  echo '{"error":"No snapshot: deploy GET /admin/runs/snapshot or run railway login"}' >&2
  exit 1
fi

# Match app config: SQLAlchemy uses psycopg v3, not psycopg2.
if [[ "$DB_PUBLIC" == postgresql://* ]]; then
  DB_PUBLIC="postgresql+psycopg://${DB_PUBLIC#postgresql://}"
elif [[ "$DB_PUBLIC" == postgres://* ]]; then
  DB_PUBLIC="postgresql+psycopg://${DB_PUBLIC#postgres://}"
fi

export DATABASE_URL="$DB_PUBLIC"
export LIMIT
exec "$PY" - <<'PY'
import json
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

limit = int(os.environ.get("LIMIT", "50"))
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    sessions = conn.execute(
        text(
            """
            SELECT id, status, phase, message, percent, error, resource_ids,
                   created_at, updated_at
            FROM analysis_sessions
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    usage = conn.execute(
        text(
            "SELECT month, tokens_in, tokens_out, cost_usd, calls "
            "FROM api_usage ORDER BY month DESC LIMIT 6"
        )
    ).mappings().all()


def ser(row):
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


out_sessions = []
by_status: dict[str, int] = {}
for row in sessions:
    s = ser(row)
    rids = s.pop("resource_ids") or []
    s["resource_count"] = len(rids)
    created = row["created_at"]
    updated = row["updated_at"]
    if created and updated:
        s["duration_sec"] = (updated - created).total_seconds()
    else:
        s["duration_sec"] = None
    by_status[s["status"]] = by_status.get(s["status"], 0) + 1
    out_sessions.append(s)

print(
    json.dumps(
        {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "summary": {"total_recent": len(out_sessions), "by_status": by_status},
            "sessions": out_sessions,
            "api_usage": [ser(u) for u in usage],
        }
    )
)
PY
