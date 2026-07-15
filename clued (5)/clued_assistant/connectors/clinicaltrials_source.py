"""
ClinicalTrials.gov connector -- active/completed clinical trial registry.

Uses the official v2 REST API (the old XML-based v1 API was retired in
2024). No key required.

    GET https://clinicaltrials.gov/api/v2/studies
        ?query.term={query}&pageSize=N&format=json

Docs: https://clinicaltrials.gov/data-api/api
"""

from __future__ import annotations

from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
API_URL = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsConnector(Connector):
    name = "clinicaltrials"
    provider_label = "ClinicalTrials.gov"
    domains = frozenset({"health"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        params = {
            "query.term": query,
            "pageSize": max_results,
            "format": "json",
        }
        try:
            resp = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            studies = resp.json().get("studies", [])
        except Exception:
            return []

        sources: List[Source] = []
        for study in studies[:max_results]:
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})

            nct_id = ident.get("nctId", "")
            title = ident.get("briefTitle", "Untitled study")
            overall_status = status.get("overallStatus", "")
            phase_list = protocol.get("designModule", {}).get("phases", [])
            phase = ", ".join(phase_list) if phase_list else ""

            snippet_bits = [b for b in (overall_status, phase) if b]
            snippet = " · ".join(snippet_bits)

            if not nct_id:
                continue

            sources.append(
                Source(
                    title=title,
                    url=f"https://clinicaltrials.gov/study/{nct_id}",
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="health",
                    extra={"status": overall_status},
                )
            )
        return sources
