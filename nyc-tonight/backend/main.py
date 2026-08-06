"""NYC Tonight Agent Lab API.

POST /chat runs the tool-use loop and returns reply text, result cards,
and a structured ``trace`` for Lesson 1 notes and the What's happening panel.
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

from agent_loop import run_agent  # noqa: E402
from providers import ollama_reachable, provider_info  # noqa: E402
from tools import tool_sources_status  # noqa: E402

app = FastAPI(title="NYC Tonight Agent Lab", version="0.2.0")

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
    trace: dict = Field(default_factory=dict)


@app.get("/")
def root():
    return {"service": "nyc-tonight-agent-lab", "status": "ok", "version": "0.2.0"}


@app.get("/health")
def health():
    info = provider_info()
    return {
        "status": "ok",
        "service": "nyc-tonight-agent-lab",
        "provider": info.name,
        "model": info.model,
        "provider_configured": info.configured,
        "provider_detail": info.detail,
        "ollama_reachable": ollama_reachable() if info.name == "ollama" else None,
        "groq_configured": bool((os.getenv("GROQ_API_KEY") or "").strip()),
        "tools": tool_sources_status(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    logger.info("chat: %r (history=%d turns)", req.message[:120], len(req.conversation_history))
    history = [t.model_dump() for t in req.conversation_history]
    outcome = run_agent(req.message, history)
    return ChatResponse(
        reply_text=outcome.get("reply_text", ""),
        results=outcome.get("results", []),
        trace=outcome.get("trace") or {},
    )
