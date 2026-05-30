#!/usr/bin/env sh
set -eu

case "${CATALOG_JOB:-api}" in
  sync|grow|probe)
    exec python -m findings_api.catalog.cli "$CATALOG_JOB" "$@"
    ;;
  api)
    exec uvicorn findings_api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
    ;;
  *)
    echo "Unknown CATALOG_JOB=${CATALOG_JOB} (expected api, sync, grow, probe)" >&2
    exit 1
    ;;
esac
