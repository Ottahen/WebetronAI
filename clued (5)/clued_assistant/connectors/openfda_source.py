"""
OpenFDA connector -- FDA-approved drug label data.

Searches the drug/label endpoint across brand name, generic name, and
indications, no key required (an optional OPENFDA_API_KEY raises the
rate limit).

    GET https://api.fda.gov/drug/label.json
        ?search=openfda.brand_name:"{q}"+openfda.generic_name:"{q}"+indications_and_usage:"{q}"
        &limit=N

Docs: https://open.fda.gov/apis/drug/label/
"""

from __future__ import annotations

import os
from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
API_URL = "https://api.fda.gov/drug/label.json"


class OpenFDAConnector(Connector):
    name = "openfda"
    provider_label = "OpenFDA"
    domains = frozenset({"health"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        q = query.replace('"', "")
        search_expr = (
            f'openfda.brand_name:"{q}" openfda.generic_name:"{q}" '
            f'indications_and_usage:"{q}"'
        )
        params = {"search": search_expr, "limit": max_results}

        api_key = os.environ.get("OPENFDA_API_KEY")
        if api_key:
            params["api_key"] = api_key

        try:
            resp = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            return []

        sources: List[Source] = []
        for item in results[:max_results]:
            openfda = item.get("openfda", {})
            brand = (openfda.get("brand_name") or [""])[0]
            generic = (openfda.get("generic_name") or [""])[0]
            title = brand or generic or "FDA drug label"

            usage = item.get("indications_and_usage", [""])[0]
            snippet = usage[:400] if usage else ""

            set_id = item.get("id", "")
            url = f"https://www.accessdata.fda.gov/spl/search?id={set_id}" if set_id else "https://open.fda.gov"

            sources.append(
                Source(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider=self.provider_label,
                    source_type="health",
                    extra={"generic_name": generic},
                )
            )
        return sources
