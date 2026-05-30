#!/usr/bin/env bash
# Run catalog sync/grow against Railway production Postgres from your machine.
# Uses DATABASE_PUBLIC_URL (reachable outside Railway); do not commit credentials.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/apps/api/.venv/bin/python"
CLI="findings_api.catalog.cli"

cmd="${1:-}"
if [[ -z "$cmd" || ! "$cmd" =~ ^(sync|grow|probe|health)$ ]]; then
  echo "Usage: $0 {sync|grow|probe|health} [extra args...]" >&2
  exit 1
fi
shift

if [[ ! -x "$PY" ]]; then
  echo "Missing API venv at apps/api/.venv — run: cd apps/api && python -m venv .venv && pip install -e ." >&2
  exit 1
fi

# Load local catalog limits (root .env); secrets stay local.
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
# Prod caps override local 10k limits when syncing production (Phase 1 / Hobby budget).
if [[ "${CATALOG_PROD:-1}" == "1" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/scripts/catalog-prod.env"
  set +a
fi

# Public Postgres URL from Railway (not postgres.railway.internal).
DB_PUBLIC="$(npx railway variable list --service Postgres -k 2>/dev/null | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2- || true)"
if [[ -z "$DB_PUBLIC" ]]; then
  echo "Could not read DATABASE_PUBLIC_URL — run: npx railway link (project faithful-radiance)" >&2
  exit 1
fi
export DATABASE_URL="$DB_PUBLIC"

cd "$ROOT/apps/api"

case "$cmd" in
  sync)
    exec "$PY" -m "$CLI" sync "$@"
    ;;
  grow)
    exec "$PY" -m "$CLI" grow "$@"
    ;;
  probe)
    exec "$PY" -m "$CLI" probe "$@"
    ;;
  health)
    TOKEN="${ADMIN_SYNC_TOKEN:-}"
    if [[ -z "$TOKEN" ]]; then
      echo "Set ADMIN_SYNC_TOKEN in .env for prod health check" >&2
      exit 1
    fi
    exec curl -s "https://asra-production.up.railway.app/admin/catalog/health" \
      -H "Authorization: Bearer $TOKEN"
    ;;
esac
