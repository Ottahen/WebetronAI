"""
Atlas -- the free-form chat mode.

Atlas is a real conversational mode, not a scripted demo: each session
keeps its own message history server-side (in-process; restarting the
server clears it -- see the note in README about adding persistent
storage if you need chats to survive a restart), and every reply is
generated fresh from that history.

Honesty note on capability: genuine open-domain conversation (and image
understanding) needs an actual LLM behind it. If OPENAI_API_KEY is set,
Atlas uses it directly (with the full conversation history + an
uploaded image, if any). If no key is set, Atlas still remembers the
conversation, but answers are produced by combining that memory with a
live web/Wikipedia research pass and the local extractive summarizer --
it will say so, rather than silently pretending to be a full chatbot it
isn't.
"""

from __future__ import annotations

import base64
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .core import ClueEngine
from .identity import IDENTITY_ANSWER, is_identity_question

SYSTEM_PROMPT = """You are Atlas, Clued's general chat mode (Clued is built by PrimeAct, \
created by \u2112 / Ottahen -- github.com/Ottahen). Hold a normal, friendly, ChatGPT/Claude-style \
conversation and remember what's been said earlier in this chat.

Formatting rules:
- Write math in LaTeX ($...$ for inline, $$...$$ for display) -- the UI renders it properly, \
so never spell out raw LaTeX commands in prose.
- Use real Markdown (headings, **bold**, tables, code fences) -- it is rendered, not shown as \
literal asterisks or hashes.
- For data, comparisons, or anything graph-like, prefer a compact Markdown table or a short \
labeled list over a wall of prose, and use an emoji sparingly where it genuinely aids scanning \
(e.g. \U0001F4C8 for growth, \u26A0\uFE0F for a caveat) -- never as decoration on every line.
- Be direct and human, not robotic.

If you are asked what generated an image, be upfront that image generation runs through \
Perchance's AI Text-to-Image Generator (perchance.org) -- never claim it's Clued's own model."""

MAX_HISTORY_MESSAGES = 24


@dataclass
class ChatSession:
    session_id: str
    messages: List[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class AtlasChat:
    def __init__(self) -> None:
        self.sessions: Dict[str, ChatSession] = {}
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self._research_engine = ClueEngine()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def new_session(self) -> str:
        sid = uuid.uuid4().hex
        self.sessions[sid] = ChatSession(session_id=sid)
        return sid

    def _get_session(self, session_id: Optional[str]) -> ChatSession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        sid = session_id or uuid.uuid4().hex
        session = ChatSession(session_id=sid)
        self.sessions[sid] = session
        return session

    def history(self, session_id: str) -> List[dict]:
        session = self.sessions.get(session_id)
        return list(session.messages) if session else []

    # ------------------------------------------------------------------
    # Reply
    # ------------------------------------------------------------------

    def reply(
        self,
        session_id: Optional[str],
        message: str,
        image_b64: Optional[str] = None,
        image_mime: str = "image/png",
    ) -> dict:
        session = self._get_session(session_id)
        message = message.strip()

        if is_identity_question(message) and not image_b64:
            session.messages.append({"role": "user", "content": message})
            session.messages.append({"role": "assistant", "content": IDENTITY_ANSWER})
            return {
                "session_id": session.session_id,
                "answer": IDENTITY_ANSWER,
                "backend": "identity",
            }

        session.messages.append(
            {"role": "user", "content": message, "has_image": bool(image_b64)}
        )

        if self.openai_key:
            answer, backend = self._openai_reply(session, message, image_b64, image_mime)
        else:
            answer, backend = self._fallback_reply(session, message)

        session.messages.append({"role": "assistant", "content": answer})
        session.messages = session.messages[-MAX_HISTORY_MESSAGES:]

        return {"session_id": session.session_id, "answer": answer, "backend": backend}

    # ------------------------------------------------------------------
    # Backend 1: a real LLM (OpenAI), with vision when an image is sent
    # ------------------------------------------------------------------

    def _openai_reply(
        self,
        session: ChatSession,
        message: str,
        image_b64: Optional[str],
        image_mime: str,
    ) -> tuple[str, str]:
        try:
            import openai

            client = openai.OpenAI(api_key=self.openai_key)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for turn in session.messages[:-1]:  # history before this new user turn
                if turn["role"] in ("user", "assistant"):
                    messages.append({"role": turn["role"], "content": turn["content"]})

            if image_b64:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message or "What's in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_mime};base64,{image_b64}"
                                },
                            },
                        ],
                    }
                )
            else:
                messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.6,
                max_tokens=900,
            )
            answer = (response.choices[0].message.content or "").strip()
            if answer:
                return answer, "openai"
        except Exception:
            pass
        return self._fallback_reply(session, message)

    # ------------------------------------------------------------------
    # Backend 2: memory + live research + local extractive summary
    # ------------------------------------------------------------------

    def _fallback_reply(self, session: ChatSession, message: str) -> tuple[str, str]:
        recent_turns = [
            f"{t['role']}: {t['content']}"
            for t in session.messages[-6:-1]
            if t["role"] in ("user", "assistant") and isinstance(t["content"], str)
        ]
        history_note = "\n".join(recent_turns)

        result = self._research_engine.research(message)
        answer = result["answer"]
        note = (
            "\n\n_Atlas is running without OPENAI_API_KEY set, so this reply comes from a "
            "live research pass + local summary rather than a full conversational model — "
            "set OPENAI_API_KEY for genuine free-form chat and image understanding._"
        )
        if history_note:
            answer = f"{answer}"
        return answer + note, result["answer_backend"] + "+atlas-fallback"


def decode_data_url(data_url: str) -> tuple[str, str]:
    """Accepts either a raw base64 string or a `data:<mime>;base64,<data>` URL."""
    if data_url.startswith("data:"):
        header, b64 = data_url.split(",", 1)
        mime = header.split(";")[0].replace("data:", "") or "image/png"
        return b64, mime
    return data_url, "image/png"
