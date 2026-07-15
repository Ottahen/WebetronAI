"""
Lightweight, dependency-free query classifier.

Clued doesn't hit every connector for every question -- that would be slow
and noisy (nobody wants ClinicalTrials.gov results for "capital of France").
Instead, a query is scored against a few keyword sets to decide which extra,
domain-specific connectors are worth activating. DuckDuckGo and Wikipedia
always run as the general-purpose baseline.

This is intentionally simple (substring matching, no ML) so it's fast,
transparent, and has zero extra dependencies or model downloads. It's easy
to extend: add words to a set, or add a new domain entirely.
"""

from __future__ import annotations

from typing import Set

DOMAIN_KEYWORDS = {
    "health": {
        "health", "disease", "symptom", "symptoms", "drug", "medication",
        "medicine", "treatment", "therapy", "clinical trial", "trial",
        "vaccine", "cancer", "diabetes", "virus", "infection", "dosage",
        "side effect", "side effects", "pandemic", "patient", "diagnosis",
        "syndrome", "fda", "pharma", "pharmaceutical", "surgery", "doctor",
        "condition", "disorder", "mental health", "nutrition", "pubmed",
    },
    "finance": {
        "gdp", "inflation", "unemployment", "interest rate", "stock",
        "stocks", "sec filing", "10-k", "10-q", "8-k", "earnings",
        "economy", "economic", "fiscal", "federal reserve", "treasury",
        "market cap", "revenue", "ticker", "nasdaq", "nyse", "investor",
        "investment", "shares", "ipo", "quarterly report", "annual report",
        "world bank", "imf", "recession", "exchange rate", "trade deficit",
    },
    "academic": {
        "paper", "papers", "study", "studies", "research", "arxiv",
        "algorithm", "theorem", "hypothesis", "dataset", "preprint",
        "journal", "citation", "peer-reviewed", "quantum", "neural network",
        "machine learning", "physics", "biology", "chemistry research",
        "publication", "scholar",
    },
    "geospatial": {
        "map", "location", "where is", "coordinates", "latitude",
        "longitude", "near me", "distance between", "address of",
        "border", "geocode", "city of", "capital of",
    },
}


def classify(query: str) -> Set[str]:
    """Return the set of domains a query touches on (possibly empty)."""
    q = f" {query.lower()} "
    hits: Set[str] = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                hits.add(domain)
                break
    return hits
