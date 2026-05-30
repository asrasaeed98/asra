#!/usr/bin/env bash
# Configure Railway catalog-sync + catalog-grow cron services (Option A).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_ID="162374b0-fd7f-4881-90d8-633e293cfba4"
ASRA_SERVICE="asra"
SYNC_ID="9e34cd85-b984-4a5a-9878-21b602a61456"
GROW_ID="074072ab-a006-4d7e-be21-50a65b66704b"
REPO="asrasaeed98/asra"

railway_token() {
  python3 - <<'PY'
import json, pathlib
print(json.loads(pathlib.Path.home().joinpath(".railway/config.json").read_text())["user"]["accessToken"])
PY
}

railway_gql() {
  curl -s -X POST https://backboard.railway.com/graphql/v2 \
    -H "Authorization: Bearer $(railway_token)" \
    -H "Content-Type: application/json" \
    --data-binary @"$1"
}

copy_catalog_vars() {
  local target="$1"
  echo "Copying catalog env vars to ${target}..."
  while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue
    case "$key" in
      RAILWAY_*|CORS_ORIGINS|SESSION_DATA_DIR|ANTHROPIC_API_KEY|ADMIN_SYNC_TOKEN) continue ;;
    esac
    printf '%s' "$value" | npx railway variable set "$key" --stdin --service "$target" --skip-deploys --json >/dev/null
  done < <(npx railway variable list --service "$ASRA_SERVICE" -k 2>/dev/null | grep -v '^RAILWAY_')
}

configure_cron_service() {
  local sid="$1" name="$2" config_file="$3" cron="$4" catalog_job="$5"
  local tmp
  tmp="$(mktemp)"

  cat >"$tmp" <<EOF
{"query":"mutation(\$id: String!, \$input: ServiceConnectInput!) { serviceConnect(id: \$id, input: \$input) { id } }","variables":{"id":"${sid}","input":{"repo":"${REPO}"}}}
EOF
  echo "Connecting ${name} to ${REPO}..."
  railway_gql "$tmp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'errors' not in d, d.get('errors')"

  cat >"$tmp" <<EOF
{"query":"mutation(\$serviceId: String!, \$environmentId: String!, \$input: ServiceInstanceUpdateInput!) { serviceInstanceUpdate(serviceId: \$serviceId, environmentId: \$environmentId, input: \$input) { id } }","variables":{"serviceId":"${sid}","environmentId":"${ENV_ID}","input":{"railwayConfigFile":"${config_file}","cronSchedule":"${cron}","restartPolicyType":"NEVER","dockerfilePath":"Dockerfile"}}}
EOF
  echo "Configuring ${name} (cron=${cron}, job=${catalog_job})..."
  railway_gql "$tmp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'errors' not in d, d.get('errors')"

  npx railway variable set "CATALOG_JOB=${catalog_job}" --service "$name" --skip-deploys --json >/dev/null
  npx railway variable set CATALOG_SYNC_INTERVAL_HOURS=0 --service "$name" --skip-deploys --json >/dev/null
  npx railway variable set CATALOG_PROBE_INTERVAL_HOURS=0 --service "$name" --skip-deploys --json >/dev/null
  copy_catalog_vars "$name"
  rm -f "$tmp"
}

echo "Disabling in-process catalog schedulers on ${ASRA_SERVICE}..."
npx railway variable set CATALOG_SYNC_INTERVAL_HOURS=0 --service "$ASRA_SERVICE" --json >/dev/null
npx railway variable set CATALOG_PROBE_INTERVAL_HOURS=0 --service "$ASRA_SERVICE" --json >/dev/null

configure_cron_service "$SYNC_ID" "catalog-sync" "/railway/catalog-sync.toml" "0 3 * * 0" "sync"
configure_cron_service "$GROW_ID" "catalog-grow" "/railway/catalog-grow.toml" "0 4 * * *" "grow"

echo "Deploying catalog-sync (initial sync run)..."
npx railway up --service catalog-sync --detach --message "catalog-sync cron setup"

echo "Deploying catalog-grow..."
npx railway up --service catalog-grow --detach --message "catalog-grow cron setup"

echo "Redeploying asra (entrypoint + scheduler off)..."
npx railway up --service asra --detach --message "catalog entrypoint"

echo "Done. Monitor: npx railway logs --service catalog-sync"
