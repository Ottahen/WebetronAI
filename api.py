#!/usr/bin/env python3
"""
FastAPI REST API for the AI Web Research Assistant.

Run with:
    uvicorn api:app --reload --port 8000

Example request:
    curl -X POST http://localhost:8000/research \
         -H "Content-Type: application/json" \
         -d '{"query": "What is quantum computing?"}'
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from ai_researcher import ResearchAssistant

app = FastAPI(title="AI Web Research Assistant API")


class ResearchRequest(BaseModel):
    query: str
    web_results: int = 4


class ResearchResponse(BaseModel):
    query: str
    answer: str
    wikipedia_summary: str | None
    wikipedia_url: str | None
    sources: list[dict]


@app.get("/")
def root() -> dict:
    return {"message": "AI Web Research Assistant API. POST /research to ask a question."}


@app.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest) -> dict:
    assistant = ResearchAssistant(max_web_results=req.web_results)
    result = assistant.research(req.query)
    return result
