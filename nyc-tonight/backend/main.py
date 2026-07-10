"""NYC Tonight — FastAPI backend.

One primary endpoint: POST /chat. It runs the Claude tool-use loop
(``claude_client.run_agent``) and returns a conversational reply plus
structured result cards for the frontend.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("nyc_tonight")

from claude_client import run_agent  # noqa: E402  (import after env is loaded)

app = FastAPI(title="NYC Tonight API", version="0.1.0")

# CORS: allow the Vercel frontend origin(s). Comma-separated list in env, or
# "*" for local/dev convenience.
_origins_raw = os.getenv("CORS_ORIGINS", "*").strip()
if _origins_raw == "*" or not _origins_raw:
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply_text: str
    results: list[dict] = Field(default_factory=list)


@app.get("/")
def root():
    return {"service": "nyc-tonight-api", "status": "ok", "version": "0.1.0"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nyc-tonight-api",
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "yelp_configured": bool(os.getenv("YELP_API_KEY")),
        "google_places_configured": bool(os.getenv("GOOGLE_PLACES_API_KEY")),
        "ticketmaster_configured": bool(os.getenv("TICKETMASTER_API_KEY")),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    logger.info("chat: %r (history=%d turns)", req.message[:120], len(req.conversation_history))
    history = [t.model_dump() for t in req.conversation_history]
    outcome = run_agent(req.message, history)
    return ChatResponse(
        reply_text=outcome.get("reply_text", ""),
        results=outcome.get("results", []),
    )
