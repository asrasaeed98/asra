#!/usr/bin/env bash
# Bootstrap production catalog_resources from the local API database.
# Local: apps/api settings (.env / sqlite or docker Postgres).
# Prod: Railway DATABASE_PUBLIC_URL (same pattern as railway-catalog.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/apps/api/.venv/bin/python"
BOOT="${ROOT}/scripts/catalog_bootstrap_prod.py"

if [[ ! -x "$PY" ]]; then
  echo "Missing API venv at apps/api/.venv" >&2
  exit 1
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

DB_PUBLIC="$(npx railway variable list --service Postgres -k 2>/dev/null | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2- || true)"
if [[ -z "$DB_PUBLIC" ]]; then
  echo "Could not read DATABASE_PUBLIC_URL — run: npx railway link" >&2
  exit 1
fi
export DATABASE_URL="$DB_PUBLIC"

echo "Bootstrapping catalog_resources to production..."
exec "$PY" "$BOOT"
