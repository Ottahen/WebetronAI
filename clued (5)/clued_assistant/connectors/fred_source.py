"""
FRED (Federal Reserve Economic Data) connector.

Unlike the other connectors, FRED *requires* a free API key -- there's no
keyless tier. Get one at https://fred.stlouisfed.org/docs/api/api_key.html
and set FRED_API_KEY. Without it, this connector silently returns no
results (the same "optional, degrades gracefully" pattern the original
project uses for OPENAI_API_KEY).

    1. series/search       -- find a matching series for the query
    2. series/observations -- fetch its latest value

Docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import os
from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
BASE_URL = "https://api.stlouisfed.org/fred"


class FREDConnector(Connector):
    name = "fred"
    provider_label = "FRED"
    domains = frozenset({"finance"})

    def search(self, query: str, max_results: int = 2) -> List[Source]:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            return []

        try:
            resp = requests.get(
                f"{BASE_URL}/series/search",
                params={
                    "search_text": query,
                    "api_key": api_key,
                    "file_type": "json",
                    "limit": max_results,
                },
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            series_list = resp.json().get("seriess", [])
        except Exception:
            return []

        sources: List[Source] = []
        for series in series_list[:max_results]:
            series_id = series.get("id")
            title = series.get("title", "Untitled series")
            if not series_id:
                continue

            latest_value, latest_date = self._latest_observation(series_id, api_key)
            snippet = f"{latest_value} ({latest_date})" if latest_value else series.get("notes", "")[:300]

            sources.append(
                Source(
                    title=title,
                    url=f"https://fred.stlouisfed.org/series/{series_id}",
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="finance",
                    extra={"series_id": series_id},
                )
            )
        return sources

    @staticmethod
    def _latest_observation(series_id: str, api_key: str):
        try:
            resp = requests.get(
                f"{BASE_URL}/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                return obs[0].get("value"), obs[0].get("date")
        except Exception:
            pass
        return None, None
