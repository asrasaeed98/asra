# Findings.ai Web

Next.js frontend for Findings.ai Phase 1.

## Development

```bash
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env.local` (repo root `.env.example`).

## Routes

| Path | Step |
|------|------|
| `/` | Landing |
| `/search` | Dataset search |
| `/review` | Confirm filters / ML |
| `/analyze` | Progress (demo timer until worker wired) |
| `/results` | Findings + AI summary + chat |
