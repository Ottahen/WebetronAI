"""
SEC EDGAR connector -- full-text search across public company filings.

Uses the free EDGAR Full-Text Search System (EFTS), no key required, but
the SEC's fair-access policy asks for an identifying User-Agent header.

    GET https://efts.sec.gov/LATEST/search-index?q={query}&forms=10-K,10-Q,8-K

Docs: https://www.sec.gov/edgar/search/
"""

from __future__ import annotations

from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
API_URL = "https://efts.sec.gov/LATEST/search-index"
HEADERS = {"User-Agent": "Clued Research Assistant contact@example.com"}


class SECEdgarConnector(Connector):
    name = "sec_edgar"
    provider_label = "SEC EDGAR"
    domains = frozenset({"finance"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        params = {"q": f'"{query}"', "forms": "10-K,10-Q,8-K"}
        try:
            resp = requests.get(
                API_URL, params=params, headers=HEADERS, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
        except Exception:
            return []

        sources: List[Source] = []
        for hit in hits[:max_results]:
            src = hit.get("_source", {})
            display_names = src.get("display_names", [])
            company = display_names[0] if display_names else "Unknown filer"
            form_type = src.get("root_form") or (src.get("forms") or [""])[0]
            file_date = src.get("file_date", "")

            ciks = src.get("ciks") or []
            doc_id = hit.get("_id", "")
            url = "https://www.sec.gov/cgi-bin/browse-edgar"
            if ciks and ":" in doc_id:
                accession_nodash, filename = doc_id.split(":", 1)
                cik = str(int(ciks[0]))
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}"

            title = f"{company} — {form_type}" if form_type else company
            snippet = f"Filed {file_date}" if file_date else ""

            sources.append(
                Source(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="finance",
                    extra={"form_type": form_type, "file_date": file_date},
                )
            )
        return sources
