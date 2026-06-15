# Findings ops dashboard (local)

Cursor Canvas for production metrics: analysis runs, timing, failures, AI spend, and **unique anonymous visitors**.

## Files

| File | Purpose |
|------|---------|
| `findings-ops-dashboard.canvas.tsx` | Dashboard source (committed to repo) |
| `regenerate-canvas.py` | Pull prod data and refresh the canvas |

## Refresh data

From repo root (needs `ADMIN_SYNC_TOKEN` in `.env`):

```bash
apps/api/.venv/bin/python tools/ops-dashboard/regenerate-canvas.py
```

This writes:

1. `tools/ops-dashboard/findings-ops-dashboard.canvas.tsx` (local copy in repo)
2. `~/.cursor/projects/Users-asrasaeed-asra/canvases/findings-ops-dashboard.canvas.tsx` (Cursor side panel)

Open the canvas in Cursor beside chat, or ask the agent: *"refresh the ops dashboard"*.

## Unique visitors

After deploying the web + API changes:

- Each browser gets an anonymous UUID in `localStorage` (`findings_visitor_id`)
- Page views POST to `POST /metrics/visit`
- Analysis sessions store `visitor_id` when started from Review

Metrics appear on the dashboard after traffic accumulates. Same person on two devices = two visitors.

## Data sources

- **Preferred:** `GET /admin/ops/dashboard` (full metrics incl. visitors)
- **Fallback:** `scripts/build-partial-ops-data.py` (partial; no visitors until API deploy)
