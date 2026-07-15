"""
Connector registry.

Add a new data source by writing a Connector subclass anywhere in this
package and appending an instance to ALL_CONNECTORS below. The router
(see ../router.py) decides which of these actually run for a given query
based on each connector's `.domains`.
"""

from __future__ import annotations

from typing import List

from .base import Connector, Source
from .duckduckgo import DuckDuckGoConnector
from .wikipedia_source import WikipediaConnector
from .arxiv_source import ArxivConnector
from .openalex_source import OpenAlexConnector
from .pubmed_source import PubMedCentralConnector
from .clinicaltrials_source import ClinicalTrialsConnector
from .openfda_source import OpenFDAConnector
from .secedgar_source import SECEdgarConnector
from .worldbank_source import WorldBankConnector
from .fred_source import FREDConnector
from .openstreetmap_source import OpenStreetMapConnector

ALL_CONNECTORS: List[Connector] = [
    DuckDuckGoConnector(),
    WikipediaConnector(),
    ArxivConnector(),
    OpenAlexConnector(),
    PubMedCentralConnector(),
    ClinicalTrialsConnector(),
    OpenFDAConnector(),
    SECEdgarConnector(),
    WorldBankConnector(),
    FREDConnector(),
    OpenStreetMapConnector(),
]

__all__ = ["Connector", "Source", "ALL_CONNECTORS"]
