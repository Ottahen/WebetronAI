"""
Shared types for all Clued data-source connectors.

Every connector (DuckDuckGo, Wikipedia, arXiv, OpenAlex, PubMed Central,
ClinicalTrials.gov, OpenFDA, SEC EDGAR, World Bank, FRED, OpenStreetMap...)
returns a list of `Source` objects through a common `.search()` interface.
This lets the core engine treat every provider identically: run it, catch
its failures, merge its results, move on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Source:
    """A single citable result returned by a connector."""

    title: str
    url: str
    snippet: str
    provider: str                 # human-readable provider name, e.g. "PubMed Central"
    source_type: str = "web"      # web | encyclopedia | academic | health | finance | geospatial
    extra: Dict[str, str] = field(default_factory=dict)  # provider-specific extras (date, status, etc.)


class Connector:
    """Base class every data-source connector implements."""

    #: short machine name, e.g. "pubmed"
    name: str = "connector"
    #: label shown in the UI's source cards, e.g. "PubMed Central"
    provider_label: str = "Source"
    #: the query domains (see router.py) this connector should activate for.
    #: an empty set means "always run" (used for the general-purpose baseline).
    domains: Set[str] = frozenset()

    def is_relevant(self, query: str, domains: Set[str]) -> bool:
        """Should this connector run for this query?

        Default: run if this connector has no domain restriction, or if any
        of its domains overlap with the query's classified domains.
        """
        if not self.domains:
            return True
        return bool(self.domains & domains)

    def search(self, query: str, max_results: int = 3) -> List[Source]:  # pragma: no cover
        raise NotImplementedError
