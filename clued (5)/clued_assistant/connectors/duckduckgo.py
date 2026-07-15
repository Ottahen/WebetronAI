"""
General web search -- the always-on baseline connector.

Uses DuckDuckGo (via the `ddgs` package) by default, which needs no API
key. If SERPAPI_API_KEY is set, real Google results are used instead.
"""

from __future__ import annotations

import os
from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10


class DuckDuckGoConnector(Connector):
    name = "web_search"
    provider_label = "Web"
    domains = frozenset()  # always relevant

    def search(self, query: str, max_results: int = 4) -> List[Source]:
        serpapi_key = os.environ.get("SERPAPI_API_KEY")
        if serpapi_key:
            sources = self._search_serpapi(query, max_results, serpapi_key)
            if sources:
                return sources
        return self._search_duckduckgo(query, max_results)

    def _search_serpapi(self, query: str, max_results: int, api_key: str) -> List[Source]:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": api_key, "engine": "google", "num": max_results},
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            results = resp.json().get("organic_results", [])
        except Exception:
            return []

        return [
            Source(
                title=item.get("title", "Untitled"),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                provider="Google (SerpAPI)",
                source_type="web",
            )
            for item in results[:max_results]
        ]

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Source]:
        try:
            from ddgs import DDGS
        except ImportError:
            return []

        sources: List[Source] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    sources.append(
                        Source(
                            title=r.get("title", "Untitled"),
                            url=r.get("href", ""),
                            snippet=r.get("body", ""),
                            provider=self.provider_label,
                            source_type="web",
                        )
                    )
        except Exception:
            return []
        return sources
