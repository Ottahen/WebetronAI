"""
OpenAlex connector -- 240M+ scholarly works, for academic / scientific queries.

    GET https://api.openalex.org/works?search={query}&per_page=N

As of Feb 2026, OpenAlex requires a free API key for reliable access
(unauthenticated requests get a small daily "testing" credit allowance).
Get one at https://openalex.org and set OPENALEX_API_KEY. Setting
OPENALEX_MAILTO (your email) is also recommended -- OpenAlex gives faster,
more reliable service to requests that identify a contact ("the polite
pool"), key or no key.

Docs: https://docs.openalex.org
"""

from __future__ import annotations

import os
from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10


class OpenAlexConnector(Connector):
    name = "openalex"
    provider_label = "OpenAlex"
    domains = frozenset({"academic"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        params = {"search": query, "per_page": max_results}

        api_key = os.environ.get("OPENALEX_API_KEY")
        if api_key:
            params["api_key"] = api_key

        mailto = os.environ.get("OPENALEX_MAILTO")
        if mailto:
            params["mailto"] = mailto

        try:
            resp = requests.get(
                "https://api.openalex.org/works", params=params, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        sources: List[Source] = []
        for work in data.get("results", [])[:max_results]:
            title = work.get("title") or work.get("display_name") or "Untitled"
            url = work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or work.get("id", "")

            oa = work.get("open_access", {}) or {}
            year = work.get("publication_year", "")
            cited_by = work.get("cited_by_count", 0)
            snippet = f"{year} · cited by {cited_by}" if year else f"cited by {cited_by}"
            if oa.get("is_oa"):
                snippet += " · open access"

            if not url:
                continue

            sources.append(
                Source(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="academic",
                    extra={"cited_by_count": str(cited_by)},
                )
            )
        return sources
