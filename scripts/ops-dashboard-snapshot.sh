#!/usr/bin/env bash
# Rich ops dashboard JSON for Findings (Cursor Canvas refresh).
# Prefers GET /admin/ops/dashboard; falls back to direct Postgres.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-https://asra-production.up.railway.app}"
LIMIT="${LIMIT:-200}"
DAYS="${DAYS:-30}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PY="${ROOT}/apps/api/.venv/bin/python"

if [[ -n "${ADMIN_SYNC_TOKEN:-}" ]]; then
  if curl -sf "${API_URL}/admin/ops/dashboard?limit=${LIMIT}&days=${DAYS}" \
    -H "Authorization: Bearer ${ADMIN_SYNC_TOKEN}" 2>/dev/null; then
    exit 0
  fi
fi

if [[ -x "$PY" ]]; then
  if "$PY" "$ROOT/scripts/build-partial-ops-data.py" 2>/dev/null; then
    exit 0
  fi
fi
if [[ ! -x "$PY" ]]; then
  echo '{"error":"No snapshot: deploy GET /admin/ops/dashboard or install apps/api/.venv"}' >&2
  exit 1
fi

DB_PUBLIC="${DATABASE_PUBLIC_URL:-}"
if [[ -z "$DB_PUBLIC" ]]; then
  DB_PUBLIC="$(npx railway variable list --service Postgres -k 2>/dev/null \
    | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2- || true)"
fi
if [[ -z "$DB_PUBLIC" ]]; then
  echo '{"error":"No snapshot: deploy GET /admin/ops/dashboard or set DATABASE_PUBLIC_URL"}' >&2
  exit 1
fi

if [[ "$DB_PUBLIC" == postgresql://* ]]; then
  DB_PUBLIC="postgresql+psycopg://${DB_PUBLIC#postgresql://}"
elif [[ "$DB_PUBLIC" == postgres://* ]]; then
  DB_PUBLIC="postgresql+psycopg://${DB_PUBLIC#postgres://}"
fi

export DATABASE_URL="$DB_PUBLIC"
export LIMIT DAYS
exec "$PY" - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__) or ".", "..", "apps", "api", "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from findings_api.ops_dashboard import build_ops_dashboard

limit = int(os.environ.get("LIMIT", "200"))
days = int(os.environ.get("DAYS", "30"))
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)
with Session() as db:
    print(json.dumps(build_ops_dashboard(db, limit=limit, days=days)))
PY
