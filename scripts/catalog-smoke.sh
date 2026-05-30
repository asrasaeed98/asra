#!/usr/bin/env bash
# Phase 5 — post-sync smoke checks (prod API + optional admin health).
set -euo pipefail

API_URL="${API_URL:-https://asra-production.up.railway.app}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== GET /health =="
curl -sf "${API_URL}/health" | python3 -m json.tool

echo ""
echo "== GET /search?q=gdp&limit=3 =="
curl -sf "${API_URL}/search?q=gdp&limit=3" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('total:', d.get('total', 0))
for r in d.get('results', [])[:3]:
    print(' -', r.get('title', '')[:70])
"

if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
fi
if [[ -n "${ADMIN_SYNC_TOKEN:-}" ]]; then
  echo ""
  echo "== GET /admin/catalog/health =="
  curl -sf "${API_URL}/admin/catalog/health" \
    -H "Authorization: Bearer ${ADMIN_SYNC_TOKEN}" | python3 -m json.tool
fi
