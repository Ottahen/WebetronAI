"""
OpenStreetMap connector -- geocoding via the Nominatim search API.

Free, no key required, but Nominatim's usage policy requires an
identifying User-Agent and limits usage to ~1 request/second. For
production-scale geospatial lookups, self-host Nominatim or use a
commercial provider -- this connector is fine for occasional,
research-assistant-style lookups.

    GET https://nominatim.openstreetmap.org/search?q={query}&format=jsonv2

Docs: https://nominatim.org/release-docs/latest/api/Search/
"""

from __future__ import annotations

from typing import List

import requests

from .base import Connector, Source

TIMEOUT_SECONDS = 10
API_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "Clued Research Assistant contact@example.com"}


class OpenStreetMapConnector(Connector):
    name = "openstreetmap"
    provider_label = "OpenStreetMap"
    domains = frozenset({"geospatial"})

    def search(self, query: str, max_results: int = 3) -> List[Source]:
        params = {"q": query, "format": "jsonv2", "limit": max_results}
        try:
            resp = requests.get(
                API_URL, params=params, headers=HEADERS, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            results = resp.json()
        except Exception:
            return []

        sources: List[Source] = []
        for place in results[:max_results]:
            name = place.get("display_name", "Unknown place")
            lat = place.get("lat", "")
            lon = place.get("lon", "")
            place_type = place.get("type", "")

            sources.append(
                Source(
                    title=name.split(",")[0],
                    url=f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=14/{lat}/{lon}",
                    snippet=f"{name} · {lat}, {lon}" + (f" · {place_type}" if place_type else ""),
                    provider=self.provider_label,
                    source_type="geospatial",
                    extra={"lat": str(lat), "lon": str(lon)},
                )
            )
        return sources
