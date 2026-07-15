"""
World Bank connector -- macroeconomic indicator time series.

The World Bank API (no key required) serves indicator data keyed by an
ISO country code and an indicator code -- it isn't a free-text search
engine. So this connector maps a handful of common economic terms and
country names found in the query to World Bank codes and pulls the most
recent value. It covers the common cases (GDP, inflation, unemployment,
population, life expectancy...) for major economies; anything outside
that curated list is silently skipped rather than guessed at.

    GET https://api.worldbank.org/v2/country/{cc}/indicator/{code}
        ?format=json&mrnev=1

Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10

INDICATORS = {
    "gdp": ("NY.GDP.MKTP.CD", "GDP (current US$)"),
    "gross domestic product": ("NY.GDP.MKTP.CD", "GDP (current US$)"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
    "unemployment": ("SL.UEM.TOTL.ZS", "Unemployment (% of labor force)"),
    "population": ("SP.POP.TOTL", "Population, total"),
    "life expectancy": ("SP.DYN.LE00.IN", "Life expectancy at birth (years)"),
    "exports": ("NE.EXP.GNFS.CD", "Exports of goods and services (current US$)"),
    "imports": ("NE.IMP.GNFS.CD", "Imports of goods and services (current US$)"),
    "government debt": ("GC.DOD.TOTL.GD.ZS", "Central government debt (% of GDP)"),
    "poverty": ("SI.POV.DDAY", "Poverty headcount ratio ($2.15/day, %)"),
    "co2 emissions": ("EN.GHG.CO2.MT.CE.AR5", "CO2 emissions (Mt CO2e)"),
}

COUNTRIES = {
    "united states": "US", "usa": "US", "u.s.": "US", "america": "US",
    "united kingdom": "GB", "uk": "GB", "britain": "GB",
    "china": "CN", "india": "IN", "japan": "JP", "germany": "DE",
    "france": "FR", "brazil": "BR", "canada": "CA", "australia": "AU",
    "russia": "RU", "mexico": "MX", "nepal": "NP", "world": "WLD",
}


class WorldBankConnector(Connector):
    name = "world_bank"
    provider_label = "World Bank"
    domains = frozenset({"finance"})

    def search(self, query: str, max_results: int = 2) -> List[Source]:
        indicator = self._match_indicator(query)
        if indicator is None:
            return []
        code, label = indicator
        country_code, country_name = self._match_country(query)

        try:
            resp = requests.get(
                f"https://api.worldbank.org/v2/country/{country_code}/indicator/{code}",
                params={"format": "json", "mrnev": 1},
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            return []

        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return []

        entry = payload[1][0]
        value = entry.get("value")
        year = entry.get("date", "")
        if value is None:
            return []

        snippet = f"{value:,.2f} ({year})" if isinstance(value, (int, float)) else f"{value} ({year})"

        return [
            Source(
                title=f"{label} — {country_name}",
                url=f"https://data.worldbank.org/indicator/{code}?locations={country_code}",
                snippet=snippet,
                provider=self.provider_label,
                source_type="finance",
                extra={"year": str(year)},
            )
        ]

    @staticmethod
    def _match_indicator(query: str) -> Optional[Tuple[str, str]]:
        q = query.lower()
        for keyword, (code, label) in INDICATORS.items():
            if keyword in q:
                return code, label
        return None

    @staticmethod
    def _match_country(query: str) -> Tuple[str, str]:
        q = query.lower()
        for name, code in COUNTRIES.items():
            if name in q:
                return code, name.title()
        return "WLD", "World"
