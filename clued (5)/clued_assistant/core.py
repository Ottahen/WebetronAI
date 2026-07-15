"""
ClueEngine -- the orchestrator behind Clued.

    from clued_assistant import ClueEngine
    engine = ClueEngine()
    result = engine.research("What is quantum computing?")

Pipeline:
    1. Classify the query into domains (router.py) -- health, finance,
       academic, geospatial, or none of those (general).
    2. Run every connector whose domain matches (plus the always-on
       DuckDuckGo + Wikipedia baseline) in parallel, catching failures
       per-connector so one flaky API never sinks the whole request.
    3. Scrape full text for the top general web results, for extra
       context beyond a search snippet.
    4. Hand everything to the Summarizer to produce one answer.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from .connectors import ALL_CONNECTORS, Source
from .identity import identity_answer, is_identity_question
from .modes import DEFAULT_MODE, connectors_for_mode, get_mode
from .router import classify
from .scraper import WebScraper
from .summarizer import Summarizer

MAX_SOURCES_PER_CONNECTOR = 3
MAX_PAGES_TO_SCRAPE = 3

OPTIONAL_KEY_NOTES = {
    "finance": [
        ("FRED_API_KEY", "Set FRED_API_KEY for Federal Reserve economic series (free key)."),
    ],
    "academic": [
        ("OPENALEX_API_KEY", "Set OPENALEX_API_KEY for full OpenAlex access (free key, unauthenticated use is rate-limited)."),
    ],
}


class ClueEngine:
    def __init__(
        self,
        connectors: Optional[List] = None,
        max_results_per_connector: int = MAX_SOURCES_PER_CONNECTOR,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.connectors = connectors if connectors is not None else ALL_CONNECTORS
        self.max_results_per_connector = max_results_per_connector
        self.scraper = WebScraper()
        self.summarizer = Summarizer()
        self.progress = progress_callback or (lambda msg: None)

    def research(self, query: str, mode: str = DEFAULT_MODE) -> dict:
        query = query.strip()

        if is_identity_question(query):
            return {
                "query": query,
                "domains": ["general"],
                "answer": identity_answer(),
                "answer_backend": "identity",
                "wikipedia_summary": None,
                "wikipedia_url": None,
                "sources": [],
                "warnings": [],
            }

        mode_obj = get_mode(mode)
        domains = classify(query)
        self.progress(f"Classified domains: {sorted(domains) or ['general']}")

        mode_allowed = set(connectors_for_mode(mode_obj))
        pool = [c for c in self.connectors if c in mode_allowed] or self.connectors
        active = [c for c in pool if c.is_relevant(query, domains)]
        self.progress(f"Running {len(active)} connectors: {[c.name for c in active]}")

        sources: List[Source] = []
        with ThreadPoolExecutor(max_workers=max(4, len(active))) as pool:
            futures = {
                pool.submit(c.search, query, self.max_results_per_connector): c
                for c in active
            }
            for future in as_completed(futures):
                connector = futures[future]
                try:
                    sources.extend(future.result() or [])
                except Exception:
                    self.progress(f"{connector.name} failed, skipping")

        wiki_summary, wiki_url = self._pull_wikipedia(sources)

        self.progress("Scraping top web sources...")
        web_sources = [s for s in sources if s.source_type == "web"][:MAX_PAGES_TO_SCRAPE]
        scraped_texts = [self.scraper.fetch_text(s.url) for s in web_sources]
        # align scraped_texts with the *full* sources list positionally
        scraped_by_index = []
        web_iter = iter(scraped_texts)
        web_id_set = {id(s) for s in web_sources}
        for s in sources:
            scraped_by_index.append(next(web_iter) if id(s) in web_id_set else "")

        self.progress("Generating answer...")
        answer, backend = self.summarizer.answer(
            query, sources, scraped_by_index, wiki_summary,
            allow_llm=mode_obj.allow_llm_summarizer,
        )

        return {
            "query": query,
            "domains": sorted(domains) if domains else ["general"],
            "answer": answer,
            "answer_backend": backend,
            "wikipedia_summary": wiki_summary,
            "wikipedia_url": wiki_url,
            "sources": [
                {
                    "title": s.title,
                    "url": s.url,
                    "snippet": s.snippet,
                    "provider": s.provider,
                    "source_type": s.source_type,
                }
                for s in sources
            ],
            "warnings": self._optional_key_notes(domains),
        }

    @staticmethod
    def _pull_wikipedia(sources: List[Source]):
        for s in sources:
            if s.source_type == "encyclopedia":
                return s.snippet, s.url
        return None, None

    @staticmethod
    def _optional_key_notes(domains) -> List[str]:
        notes: List[str] = []
        for domain in domains:
            for env_var, note in OPTIONAL_KEY_NOTES.get(domain, []):
                if not os.environ.get(env_var):
                    notes.append(note)
        return notes
