#!/usr/bin/env bash
# Post-deploy checklist: API health, catalog, optional web + CORS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-https://asra-production.up.railway.app}"
WEB_URL="${1:-${VERCEL_WEB_URL:-}}"

echo "== API health =="
curl -sf "${API_URL}/health" | python3 -m json.tool

echo ""
echo "== Catalog smoke =="
API_URL="${API_URL}" "${ROOT}/scripts/catalog-smoke.sh"

if [[ -n "$WEB_URL" ]]; then
  echo ""
  "${ROOT}/scripts/setup-vercel-deploy.sh" "$WEB_URL"
else
  echo ""
  echo "Web: not configured — run ./scripts/setup-vercel-deploy.sh after Vercel deploy"
fi

echo ""
echo "Catalog automation: GitHub Actions (weekly sync Sun 03:00 UTC, daily grow 04:00 UTC)"
echo "  https://github.com/asrasaeed98/asra/actions/workflows/catalog.yml"
