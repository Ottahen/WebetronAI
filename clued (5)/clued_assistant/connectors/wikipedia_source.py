"""
Wikipedia connector -- the encyclopedic baseline, mirrored in the
"Extractive Summary" + "Wikipedia Reference" cards shown in the Clued UI.

Uses the `wikipedia` package. Falls back gracefully through disambiguation
pages and auto-suggestion, same strategy as the original ai_researcher.py.
"""

from __future__ import annotations

from typing import List, Optional

from .base import Connector, Source


class WikipediaConnector(Connector):
    name = "wikipedia"
    provider_label = "Wikipedia"
    domains = frozenset()  # always relevant

    def __init__(self) -> None:
        try:
            import wikipedia
            wikipedia.set_user_agent("CluedResearchAssistant/1.0 (contact@example.com)")
        except ImportError:
            pass

    def search(self, query: str, max_results: int = 1) -> List[Source]:
        try:
            import wikipedia
        except ImportError:
            return []

        page = self._best_page(wikipedia, query)
        if page is None:
            return []

        return [
            Source(
                title=page.title,
                url=page.url,
                snippet=page.summary,
                provider=self.provider_label,
                source_type="encyclopedia",
            )
        ]

    @staticmethod
    def _best_page(wikipedia_module, query: str) -> Optional[object]:
        wp = wikipedia_module

        def page_from_title(title: str):
            try:
                return wp.page(title, auto_suggest=False)
            except wp.DisambiguationError as e:
                try:
                    return wp.page(e.options[0], auto_suggest=False)
                except Exception:
                    return None
            except Exception:
                return None

        # 1. Direct lookup
        page = page_from_title(query)
        if page:
            return page

        # 2. Wikipedia's own search, take the first hit
        try:
            for title in wp.search(query, results=3):
                page = page_from_title(title)
                if page:
                    return page
        except Exception:
            pass

        # 3. Auto-suggest as a last resort
        try:
            return wp.page(query, auto_suggest=True)
        except Exception:
            return None
