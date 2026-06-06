#!/usr/bin/env bash
# Set Railway API CORS_ORIGINS to allow the Vercel web app (plus local dev).
# Usage: ./scripts/railway-cors.sh https://your-app.vercel.app [https://preview.vercel.app]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <production-web-url> [extra-origin ...]" >&2
  echo "Example: $0 https://asra.vercel.app" >&2
  exit 1
fi

LOCAL="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002,http://127.0.0.1:3002"
PROD_CUSTOM="https://findings.site,https://www.findings.site"
ORIGINS="$LOCAL,$PROD_CUSTOM"
for url in "$@"; do
  url="${url%/}"
  ORIGINS="${ORIGINS},${url}"
done

echo "Setting CORS_ORIGINS on Railway service 'asra'..."
npx railway variables --set "CORS_ORIGINS=${ORIGINS}" --service asra

echo "Done. Railway will redeploy the API with:"
echo "  CORS_ORIGINS=${ORIGINS}"
