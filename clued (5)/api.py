#!/usr/bin/env python3
"""
FastAPI backend for Clued.

Serves:
    GET  /                 -> the Clued web UI (static/index.html)
    POST /api/research     -> Webetron / Open mode research pipeline
    POST /api/chat         -> Atlas mode: multi-turn chat, image Q&A
    POST /api/imagegen     -> Atlas mode: image generation (via Perchance)
    GET  /api/chat/history -> replay a chat session's messages
    GET  /api/health       -> liveness check

Run with:
    uvicorn api:app --reload --port 8000

Then open http://localhost:8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from clued_assistant import ClueEngine
from clued_assistant.chat import AtlasChat, decode_data_url
from clued_assistant.imagegen import PerchanceImageGenerator
from clued_assistant.modes import DEFAULT_MODE, MODES

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Clued Research Assistant API")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

engine = ClueEngine()
atlas = AtlasChat()
imagegen = PerchanceImageGenerator()


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str
    mode: str = DEFAULT_MODE


class ResearchResponse(BaseModel):
    query: str
    mode: str
    domains: list[str]
    answer: str
    answer_backend: str
    wikipedia_summary: str | None
    wikipedia_url: str | None
    sources: list[dict]
    warnings: list[str]


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    image_data_url: Optional[str] = None  # data:<mime>;base64,<data>


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    backend: str


class ImageGenRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/modes")
def modes() -> dict:
    return {
        key: {"label": m.label, "tagline": m.tagline, "is_chat": m.is_chat}
        for key, m in MODES.items()
    }


@app.post("/api/research", response_model=ResearchResponse)
def research(req: ResearchRequest) -> dict:
    mode_key = req.mode if req.mode in MODES and not MODES[req.mode].is_chat else DEFAULT_MODE
    result = engine.research(req.query, mode=mode_key)
    result["mode"] = mode_key
    return result


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict:
    image_b64, image_mime = (None, "image/png")
    if req.image_data_url:
        image_b64, image_mime = decode_data_url(req.image_data_url)
    return atlas.reply(req.session_id, req.message, image_b64=image_b64, image_mime=image_mime)


@app.get("/api/chat/history")
def chat_history(session_id: str) -> dict:
    return {"session_id": session_id, "messages": atlas.history(session_id)}


@app.post("/api/imagegen")
def imagegen_route(req: ImageGenRequest) -> dict:
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    result = imagegen.generate(req.prompt, req.negative_prompt)
    return {
        "ok": result.ok,
        "provider": result.provider,
        "images": [{"url": img.url, "seed": img.seed} for img in result.images],
        "error": result.error,
    }


# ----------------------------------------------------------------------
# Entrypoint for Replit / any host that just runs `python api.py`
# (Replit sets $PORT for you and expects the app to bind 0.0.0.0.)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
