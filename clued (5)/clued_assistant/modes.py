"""
The three modes Clued can run in, selectable from the model dropdown in
the UI. Each mode is just a different *policy* over the same underlying
connectors/summarizer — there's no separate model per mode, "model" here
is a UI/product concept, not a literal different LLM.

    Webetron  -- the original behaviour: classify the query, run every
                 connector whose domain matches, summarize. Good default
                 for "look this up for me" questions.

    Open      -- narrow research mode restricted to three health sources
                 (PubMed Central, ClinicalTrials.gov, OpenFDA) plus the
                 always-on web/Wikipedia baseline, summarized only with
                 the local backend (OpenAI is intentionally *not* used
                 here so this mode still works with zero API keys).

    Atlas     -- free-form chat (see chat.py) instead of the
                 classify-and-fetch pipeline: multi-turn memory, image
                 understanding, image generation, and the same
                 summarizer backends as a fallback when there's no LLM
                 key configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .connectors import ALL_CONNECTORS, Connector
from .connectors.pubmed_source import PubMedCentralConnector
from .connectors.clinicaltrials_source import ClinicalTrialsConnector
from .connectors.openfda_source import OpenFDAConnector

OPEN_MODE_CONNECTOR_TYPES = (
    PubMedCentralConnector,
    ClinicalTrialsConnector,
    OpenFDAConnector,
)


@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    tagline: str
    is_chat: bool = False           # Atlas: conversational, not classify-and-fetch
    allow_llm_summarizer: bool = True  # Open mode deliberately stays local-only


MODES = {
    "webetron": Mode(
        key="webetron",
        label="Webetron",
        tagline="All-round research — fans out to every relevant source",
    ),
    "open": Mode(
        key="open",
        label="Open",
        tagline="Medical & health lookups — PubMed Central, ClinicalTrials.gov, OpenFDA",
        allow_llm_summarizer=False,
    ),
    "atlas": Mode(
        key="atlas",
        label="Atlas",
        tagline="General chat, memory, image understanding & generation",
        is_chat=True,
    ),
}

DEFAULT_MODE = "webetron"


def get_mode(key: str | None) -> Mode:
    return MODES.get((key or DEFAULT_MODE).lower(), MODES[DEFAULT_MODE])


def connectors_for_mode(mode: Mode) -> List[Connector]:
    """Which connectors this mode is allowed to run (before the router's
    per-query relevance check is applied on top)."""
    if mode.key == "open":
        return [c for c in ALL_CONNECTORS if isinstance(c, OPEN_MODE_CONNECTOR_TYPES)]
    # webetron and atlas's research fallback both get the full roster;
    # the router still decides which of these actually fire per-query.
    return ALL_CONNECTORS
