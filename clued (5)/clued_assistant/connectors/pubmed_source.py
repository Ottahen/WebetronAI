"""
PubMed Central connector -- peer-reviewed biomedical/health literature.

Two-step NCBI E-utilities call, no key required (an optional NCBI_API_KEY
raises the rate limit from 3 to 10 requests/sec):

    1. esearch  -- find PMCIDs matching the query
       https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
           ?db=pmc&term={query}&retmode=json&retmax=N

    2. esummary -- fetch title/authors/date for those PMCIDs
       https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
           ?db=pmc&id={ids}&retmode=json

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

from __future__ import annotations

import os
from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedCentralConnector(Connector):
    name = "pubmed_central"
    provider_label = "PubMed Central"
    domains = frozenset({"health"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        api_key = os.environ.get("NCBI_API_KEY")

        search_params = {
            "db": "pmc",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
        }
        if api_key:
            search_params["api_key"] = api_key

        try:
            resp = requests.get(
                f"{EUTILS_BASE}/esearch.fcgi", params=search_params, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
        except Exception:
            return []

        if not ids:
            return []

        summary_params = {"db": "pmc", "id": ",".join(ids), "retmode": "json"}
        if api_key:
            summary_params["api_key"] = api_key

        try:
            resp = requests.get(
                f"{EUTILS_BASE}/esummary.fcgi", params=summary_params, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})
        except Exception:
            return []

        sources: List[Source] = []
        for pmcid in result.get("uids", ids):
            item = result.get(pmcid, {})
            title = item.get("title", "Untitled").strip()
            pubdate = item.get("pubdate", "")
            authors = item.get("authors", [])
            author_names = ", ".join(a.get("name", "") for a in authors[:3])
            snippet = f"{author_names} ({pubdate})" if author_names else pubdate

            sources.append(
                Source(
                    title=title,
                    url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="health",
                    extra={"pubdate": pubdate},
                )
            )
        return sources
