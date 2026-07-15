"""
arXiv connector -- preprints for academic / scientific queries.

Uses arXiv's public Atom-feed API (no key required):
    https://export.arxiv.org/api/query?search_query=all:{query}&max_results=N

Docs: https://info.arxiv.org/help/api/user-manual.html
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import quote_plus

import requests

from .base import Connector, Source

ATOM_NS = "{http://www.w3.org/2005/Atom}"
TIMEOUT_SECONDS = 10


class ArxivConnector(Connector):
    name = "arxiv"
    provider_label = "arXiv"
    domains = frozenset({"academic"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        url = (
            "https://export.arxiv.org/api/query"
            f"?search_query=all:{quote_plus(query)}"
            f"&start=0&max_results={max_results}"
            "&sortBy=relevance&sortOrder=descending"
        )
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception:
            return []

        sources: List[Source] = []
        for entry in root.findall(f"{ATOM_NS}entry"):
            title_el = entry.find(f"{ATOM_NS}title")
            summary_el = entry.find(f"{ATOM_NS}summary")
            id_el = entry.find(f"{ATOM_NS}id")
            published_el = entry.find(f"{ATOM_NS}published")

            title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else "Untitled"
            summary = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""
            link = (id_el.text or "").strip() if id_el is not None else ""
            published = (published_el.text or "")[:10] if published_el is not None else ""

            if not link:
                continue

            sources.append(
                Source(
                    title=title,
                    url=link,
                    snippet=summary[:500],
                    provider=self.provider_label,
                    source_type="academic",
                    extra={"published": published},
                )
            )
        return sources
