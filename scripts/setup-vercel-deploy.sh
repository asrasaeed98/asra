#!/usr/bin/env bash
# Guide + helpers for Vercel web deploy (see docs/findings-ai/DEPLOY.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-https://asra-production.up.railway.app}"
WEB_URL="${1:-${VERCEL_WEB_URL:-}}"

echo "=== Production API ==="
if curl -sf "${API_URL}/health" | python3 -m json.tool; then
  :
else
  echo "API not reachable at ${API_URL}" >&2
  exit 1
fi

if [[ -n "$WEB_URL" ]]; then
  WEB_URL="${WEB_URL%/}"
  echo ""
  echo "=== Web smoke: ${WEB_URL} ==="
  if curl -sf -o /dev/null -w "GET /search → HTTP %{http_code}\n" "${WEB_URL}/search"; then
    echo "Web looks up."
  else
    echo "Web not reachable yet — finish Vercel deploy first." >&2
    exit 1
  fi
  echo ""
  echo "=== Railway CORS ==="
  "${ROOT}/scripts/railway-cors.sh" "$WEB_URL"
  echo ""
  echo "=== End-to-end ==="
  echo "Open ${WEB_URL}/search and run a query (e.g. gdp)."
  exit 0
fi

cat <<EOF

=== Vercel web — one-time setup ===

API is live: ${API_URL}

1. Open https://vercel.com/new → Import GitHub repo **asrasaeed98/asra**
2. Root Directory: **apps/web** (required)
3. Environment variables (Production):
     NEXT_PUBLIC_API_URL=${API_URL}
     NEXT_PUBLIC_APP_NAME=Findings
4. Deploy

Or CLI (after \`npx vercel login\`):
   cd apps/web
   npx vercel --prod \\
     -e NEXT_PUBLIC_API_URL=${API_URL} \\
     -e NEXT_PUBLIC_APP_NAME=Findings

5. After deploy, wire CORS + verify:
   ./scripts/setup-vercel-deploy.sh https://YOUR-APP.vercel.app

Or: npm run setup:vercel-deploy -- https://YOUR-APP.vercel.app

EOF

if command -v vercel >/dev/null 2>&1 || npx vercel whoami >/dev/null 2>&1; then
  echo ""
  echo "=== Vercel env (required — NEXT_PUBLIC_* is baked in at build time) ==="
  if ! npx vercel env ls 2>/dev/null | grep -q NEXT_PUBLIC_API_URL; then
    printf '%s' "${API_URL}" | npx vercel env add NEXT_PUBLIC_API_URL production
    printf '%s' "Findings" | npx vercel env add NEXT_PUBLIC_APP_NAME production
    echo "Added production env vars — redeploying..."
    cd "${ROOT}/apps/web"
    npx vercel --prod --yes
  else
    echo "NEXT_PUBLIC_API_URL already set on Vercel. Redeploy after changes:"
    echo "  cd apps/web && npx vercel --prod --yes"
  fi
else
  echo "(Vercel CLI not logged in — use the dashboard steps above.)"
fi
