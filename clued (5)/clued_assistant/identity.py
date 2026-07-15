"""
Identity answers.

When someone asks Clued what it is / who made it, we answer directly
instead of sending that question through the research or chat pipeline.
This is the *only* scripted response in the whole app — everything else
is a real answer built from real sources. Clued is always honest about
using web search, third-party APIs, and (in Atlas's image generation)
Perchance's generator; nothing here is written to make Clued claim
capabilities or origins it doesn't actually have.
"""

from __future__ import annotations

import re

NAME_PATTERNS = [
    r"\bwhat('?s| is) your name\b",
    r"\bwho are you\b",
    r"\bwho made you\b",
    r"\bwho built you\b",
    r"\bwho created you\b",
    r"\bwhat are you\b",
]

IDENTITY_ANSWER = (
    "I'm **Clued**, built by **PrimeAct** (an open GitHub organization), "
    "created by \u2112 (also known as Ottahen) \u2014 github.com/Ottahen. "
    "I do real research: I search the web and query live data sources "
    "(Wikipedia, arXiv, OpenAlex, PubMed Central, ClinicalTrials.gov, "
    "OpenFDA, SEC EDGAR, World Bank, FRED, OpenStreetMap), and in Atlas "
    "mode I can also chat, look at images, and generate images via "
    "Perchance's AI Text-to-Image Generator."
)


def is_identity_question(query: str) -> bool:
    q = query.strip().lower()
    return any(re.search(p, q) for p in NAME_PATTERNS)


def identity_answer() -> str:
    return IDENTITY_ANSWER
