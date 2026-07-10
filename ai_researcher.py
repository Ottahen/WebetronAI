"""
AI Web Research Assistant
=========================
Searches Wikipedia and the web, scrapes relevant pages, and generates
cited answers using an optional LLM or a local extractive summarizer.

Usage:
    from ai_researcher import ResearchAssistant
    assistant = ResearchAssistant()
    answer = assistant.research("What is quantum computing?")
    print(answer)
"""

from __future__ import annotations

import os
import re
import html
import random
from dataclasses import dataclass
from typing import List, Optional, Callable
from urllib.parse import urlparse, quote_plus

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import wikipedia


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

MAX_WEB_RESULTS = 4          # Number of web pages to scrape per query
MAX_CHARS_PER_PAGE = 12000   # Characters kept from each scraped page
TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Source:
    title: str
    url: str
    snippet: str


@dataclass
class SearchResult:
    query: str
    sources: List[Source]
    wiki_summary: Optional[str] = None
    wiki_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Search engines
# ---------------------------------------------------------------------------

class SearchEngine:
    """Handles queries against Wikipedia and the web.

    Uses SerpAPI for real Google results when SERPAPI_API_KEY is set;
    otherwise falls back to DuckDuckGo, which requires no API key.
    """

    def __init__(self, max_web_results: int = MAX_WEB_RESULTS):
        self.max_web_results = max_web_results
        self.serpapi_key = os.environ.get("SERPAPI_API_KEY")
        wikipedia.set_user_agent("AIResearchAssistant/1.0 (contact@example.com)")

    def search(self, query: str) -> SearchResult:
        wiki_summary, wiki_url = self._search_wikipedia(query)
        sources = self._search_web(query)
        return SearchResult(
            query=query,
            sources=sources,
            wiki_summary=wiki_summary,
            wiki_url=wiki_url,
        )

    def _search_wikipedia(self, query: str) -> tuple[Optional[str], Optional[str]]:
        # Strategy:
        # 1. Direct exact lookup (best for short topic queries).
        # 2. Collect candidate pages from Wikipedia's own search and from
        #    DuckDuckGo's site-specific Wikipedia search.
        # 3. Score candidates by keyword overlap with the query and return
        #    the best one.

        def page_from_title(title: str) -> Optional[wikipedia.WikipediaPage]:
            try:
                return wikipedia.page(title, auto_suggest=False)
            except wikipedia.DisambiguationError as e:
                try:
                    return wikipedia.page(e.options[0], auto_suggest=False)
                except Exception:
                    return None
            except Exception:
                return None

        def score(text: str, is_title: bool = False) -> int:
            qwords = set(Summarizer._tokenize(query))
            twords = set(Summarizer._tokenize(text))
            overlap = len(qwords & twords)
            weight = 4 if is_title else 1
            return overlap * weight

        candidates: List[wikipedia.WikipediaPage] = []

        # 1. Exact lookup
        exact = page_from_title(query)
        if exact:
            candidates.append(exact)

        # 2a. Wikipedia search
        try:
            for title in wikipedia.search(query, results=3):
                p = page_from_title(title)
                if p:
                    candidates.append(p)
        except Exception:
            pass

        # 2b. Auto-suggest
        try:
            p = wikipedia.page(query, auto_suggest=True)
            candidates.append(p)
        except Exception:
            pass

        # 2c. DuckDuckGo site-specific Wikipedia search
        try:
            with DDGS() as ddgs:
                wiki_results = ddgs.text(
                    f"{query} site:en.wikipedia.org", max_results=3
                )
                for r in wiki_results:
                    href = r.get("href", "")
                    if ".wikipedia.org/wiki/" not in href:
                        continue
                    title = href.split("/wiki/")[-1].replace("_", " ")
                    p = page_from_title(title)
                    if p:
                        candidates.append(p)
        except Exception:
            pass

        if not candidates:
            return None, None

        # Deduplicate by title and pick the most relevant
        seen: set = set()
        best: Optional[wikipedia.WikipediaPage] = None
        best_score = -1
        for p in candidates:
            if p.title in seen:
                continue
            seen.add(p.title)
            s = score(p.title, is_title=True) + score(p.summary[:300])
            if s > best_score:
                best_score = s
                best = p

        if best:
            return best.summary, best.url
        return None, None

    def _search_web(self, query: str) -> List[Source]:
        if self.serpapi_key:
            return self._search_serpapi(query)
        return self._search_duckduckgo(query)

    def _search_serpapi(self, query: str) -> List[Source]:
        sources: List[Source] = []
        try:
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "num": self.max_web_results,
            }
            resp = requests.get(
                "https://serpapi.com/search", params=params, timeout=TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("organic_results", [])[:self.max_web_results]:
                sources.append(
                    Source(
                        title=item.get("title", "Untitled"),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                )
        except Exception as exc:
            print(f"[SerpAPI warning] {exc}. Falling back to DuckDuckGo.")
            return self._search_duckduckgo(query)
        return sources

    def _search_duckduckgo(self, query: str) -> List[Source]:
        sources: List[Source] = []
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=self.max_web_results)
                for r in results:
                    sources.append(
                        Source(
                            title=r.get("title", "Untitled"),
                            url=r.get("href", ""),
                            snippet=r.get("body", ""),
                        )
                    )
        except Exception as exc:
            print(f"[Web search warning] {exc}")
        return sources


# ---------------------------------------------------------------------------
# Web scraper
# ---------------------------------------------------------------------------

class WebScraper:
    """Fetches and extracts readable text from arbitrary URLs."""

    def __init__(self, timeout: int = TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "text/html,application/xhtml+xml"})

    def fetch_text(self, url: str) -> str:
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = self.session.get(
                url, headers=headers, timeout=self.timeout, allow_redirects=True
            )
            response.raise_for_status()

            # Skip non-HTML content
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" not in content_type:
                return ""

            return self._extract_text(response.text, url)
        except Exception as exc:
            return f"[Could not fetch page: {exc}]"

    def _extract_text(self, html_text: str, url: str) -> str:
        soup = BeautifulSoup(html_text, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to find the main content area
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(role="main")
        )
        root = main or soup.body or soup

        paragraphs = root.find_all("p")
        if not paragraphs:
            paragraphs = root.find_all(["div", "section"])

        chunks: List[str] = []
        for p in paragraphs:
            text = p.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            if len(text) > 30:
                chunks.append(text)

        full_text = "\n\n".join(chunks)
        full_text = html.unescape(full_text)
        return full_text[:MAX_CHARS_PER_PAGE].strip()


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

class Summarizer:
    """Generates an answer from gathered sources.

    Uses OpenAI when OPENAI_API_KEY is available; otherwise falls back to a
    simple extractive summary of the most relevant sentences.
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def answer(
        self,
        query: str,
        search_result: SearchResult,
        scraped_texts: List[str],
    ) -> str:
        context = self._build_context(search_result, scraped_texts)

        if self.api_key:
            return self._llm_answer(query, context)
        return self._local_answer(query, context)

    def _build_context(
        self, search_result: SearchResult, scraped_texts: List[str]
    ) -> str:
        parts: List[str] = []
        if search_result.wiki_summary:
            parts.append("=== Wikipedia Summary ===")
            parts.append(search_result.wiki_summary)

        for i, source in enumerate(search_result.sources, start=1):
            parts.append(f"\n=== Web Source {i}: {source.title} ({source.url}) ===")
            parts.append(source.snippet)
            if i - 1 < len(scraped_texts):
                text = scraped_texts[i - 1]
                if text and not text.startswith("[Could not fetch"):
                    parts.append("\n--- Detailed page content ---")
                    parts.append(text[:3500])

        return "\n\n".join(parts)

    def _llm_answer(self, query: str, context: str) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            system_prompt = (
                "You are a helpful research assistant. Use the provided context "
                "to answer the user's question accurately. Cite sources by title "
                "or URL when possible. If the context lacks enough information, "
                "say so clearly. Keep the answer concise but informative."
            )

            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
                ],
                temperature=0.3,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            return (
                f"[OpenAI failed: {exc}. Falling back to local summary.]\n\n"
                + self._local_answer(query, context)
            )

    def _local_answer(self, query: str, context: str) -> str:
        sentences = self._split_sentences(context)
        if not sentences:
            return "No usable content was found to answer your question."

        query_words = set(self._tokenize(query))
        scored: List[tuple[float, int, str]] = []
        for idx, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, query_words)
            scored.append((score, idx, sentence))

        scored.sort(reverse=True)
        top_count = min(7, len(scored))
        top = scored[:top_count]
        # Re-order by original position for readability
        top.sort(key=lambda x: x[1])

        paragraphs: List[str] = []
        current: List[str] = []
        for _, _, sentence in top:
            current.append(sentence)
            if len(current) >= 3:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))

        summary = "\n\n".join(paragraphs)
        summary = summary[:2500]
        return (
            "Answer (local extractive summary):\n\n"
            + summary
            + "\n\nNote: Set OPENAI_API_KEY for a more natural LLM-generated answer."
        )

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        # Simple sentence splitter with noise filtering
        raw = text.replace("\n", " ")
        sentences = re.split(r'(?<=[.!?])\s+', raw)
        clean: List[str] = []
        for s in sentences:
            s = s.strip()
            # Drop source headers, URLs, and very short fragments
            if len(s) < 25:
                continue
            if "===" in s or "---" in s:
                continue
            if s.startswith("http") or s.startswith("(") and "http" in s:
                continue
            if s.count("|") > 2 or s.count("·") > 2:
                continue
            clean.append(s)
        return clean

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    @staticmethod
    def _score_sentence(sentence: str, query_words: set) -> float:
        tokens = Summarizer._tokenize(sentence)
        if not tokens:
            return 0.0
        query_overlap = len(set(tokens) & query_words)
        length_bonus = min(len(tokens) / 20.0, 2.0)
        return query_overlap * 2 + length_bonus


# ---------------------------------------------------------------------------
# Main assistant
# ---------------------------------------------------------------------------

class ResearchAssistant:
    """High-level interface: ask a question, get a researched answer."""

    def __init__(
        self,
        max_web_results: int = MAX_WEB_RESULTS,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.search_engine = SearchEngine(max_web_results=max_web_results)
        self.scraper = WebScraper()
        self.summarizer = Summarizer()
        self.progress_callback = progress_callback or (lambda msg: None)

    def research(self, query: str) -> dict:
        """Run full research pipeline and return structured results."""
        self.progress_callback(f"Searching for: {query}")
        result = self.search_engine.search(query)

        self.progress_callback("Scraping web sources...")
        scraped_texts: List[str] = []
        for source in result.sources:
            if source.url:
                text = self.scraper.fetch_text(source.url)
                scraped_texts.append(text)
            else:
                scraped_texts.append("")

        self.progress_callback("Generating answer...")
        answer = self.summarizer.answer(query, result, scraped_texts)

        return {
            "query": query,
            "answer": answer,
            "wikipedia_summary": result.wiki_summary,
            "wikipedia_url": result.wiki_url,
            "sources": [
                {"title": s.title, "url": s.url, "snippet": s.snippet}
                for s in result.sources
            ],
        }


if __name__ == "__main__":
    import json
    assistant = ResearchAssistant(progress_callback=print)
    print("=" * 60)
    query = input("Enter your research question: ").strip()
    if query:
        output = assistant.research(query)
        print("\n" + "=" * 60)
        print(json.dumps(output, indent=2, ensure_ascii=False))
