#!/usr/bin/env bash
# Print GitHub Actions secrets setup instructions (Phase 2).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_PUBLIC="$(npx railway variable list --service Postgres -k 2>/dev/null | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2- || true)"
FRED="$(grep '^FRED_API_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '"' || true)"

echo "Add these at: https://github.com/asrasaeed98/asra/settings/secrets/actions"
echo ""
echo "DATABASE_URL"
echo "  (paste Railway Postgres DATABASE_PUBLIC_URL — NOT .internal)"
if [[ -n "$DB_PUBLIC" ]]; then
  echo "  Current value starts with: ${DB_PUBLIC:0:40}..."
else
  echo "  Run: npx railway variable list --service Postgres -k | grep DATABASE_PUBLIC"
fi
echo ""
echo "FRED_API_KEY"
if [[ -n "$FRED" ]]; then
  echo "  Set from your .env (not printed)."
else
  echo "  From .env or https://fred.stlouisfed.org/docs/api/api_key.html"
fi
echo ""
echo "After pushing .github/workflows/catalog.yml, run workflow manually:"
echo "  Actions → Catalog → Run workflow → sync"
