# NYC Tonight

An AI concierge for New York City. Type a natural-language request like
_"cheap dinner in Chinatown around 7pm"_ or _"something fun happening tonight near
Williamsburg"_ and a Claude agent searches real data sources, reasons over the
results, and replies with a short answer plus result cards — restaurants with a
reservation deep-link, or events with a ticket link.

> First-agent build. Prioritizes a working end-to-end loop over completeness.
> No accounts, no database, single-session/stateless.

## Architecture

```
Frontend (React + Vite, Vercel)  --POST /chat-->  Backend (FastAPI, Railway)
                                                     └─ Claude (Anthropic) tool-use loop
                                                        ├─ search_restaurants  → Yelp Fusion (primary) / Google Places (fallback)
                                                        ├─ search_events       → Ticketmaster Discovery
                                                        └─ build_reservation_link → OpenTable/Resy deep-link URL
```

The backend sends the user message + tool definitions to Claude. Claude decides
which tool(s) to call, the backend executes the real API calls, feeds results
back, and Claude returns a final text reply. The backend returns
`{ reply_text, results: [...] }`; the frontend renders the text and a card per
result.

**Reservations are deep-link handoff only** — we open a pre-filled OpenTable/Resy
search page in a new tab. We never automate or complete bookings (ToS).

## Project layout

```
nyc-tonight/
├── backend/           # FastAPI + Claude tool-use loop
│   ├── main.py        # POST /chat, /health, CORS
│   ├── claude_client.py  # the tool-use loop
│   ├── tools.py       # tool schemas + Yelp / Google Places / Ticketmaster / reservation
│   ├── requirements.txt
│   ├── Procfile       # Railway start command
│   └── .env.example
└── frontend/          # React (Vite) single-page chat UI
    ├── src/App.jsx
    ├── src/ResultCard.jsx
    ├── src/api.js
    └── .env.example
```

## Local development

### 1. Backend (port 8000)

```bash
cd nyc-tonight/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your API keys
uvicorn main:app --reload --port 8000
```

Check it: `curl -s http://127.0.0.1:8000/health`

The app degrades gracefully: with no keys it still boots. Without
`ANTHROPIC_API_KEY` the agent replies with a setup message; without a given data
key that tool reports unavailable and Claude works with whatever it can get.

### 2. Frontend (port 5173)

```bash
cd nyc-tonight/frontend
npm install
npm run dev
```

By default it calls `http://127.0.0.1:8000`. To point elsewhere, set
`VITE_API_URL` in `frontend/.env`.

## API keys

Put these in `backend/.env` (see `backend/.env.example`):

| Var | Where to get it |
|-----|-----------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `YELP_API_KEY` | https://docs.developer.yelp.com (Fusion API) |
| `GOOGLE_PLACES_API_KEY` | Google Cloud Console → enable **Places API (New)** |
| `TICKETMASTER_API_KEY` | https://developer.ticketmaster.com (Discovery API) |

## Deploy

### Backend → Railway

1. New Railway service from this repo, **root directory** `nyc-tonight/backend`.
2. Railway auto-detects Python + `requirements.txt`; start command comes from `Procfile`.
3. Set env vars: `ANTHROPIC_API_KEY`, `YELP_API_KEY`, `GOOGLE_PLACES_API_KEY`,
   `TICKETMASTER_API_KEY`, and `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`.
4. Note the public URL (e.g. `https://nyc-tonight-api.up.railway.app`).

### Frontend → Vercel

1. New Vercel project, **root directory** `nyc-tonight/frontend` (framework: Vite).
2. Set env var `VITE_API_URL=https://<your-railway-backend-url>`.
3. Deploy. Then make sure the Railway `CORS_ORIGINS` includes the Vercel URL.

## Notes / guardrails

- No browser automation against OpenTable/Resy — deep-link handoff only.
- No database or auth in v1; conversation state lives in the browser only.
- The frontend sends `conversation_history` so Claude has short-term context
  within a page session (cleared on reload).
```
