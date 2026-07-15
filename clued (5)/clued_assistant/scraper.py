"""
Fetches a URL and extracts readable body text, so the summarizer has more
to work with than just a search-result snippet. Failures (blocked
requests, non-HTML content, timeouts) are swallowed and reported as an
empty string -- one unreachable page should never take down a whole
research run.
"""

from __future__ import annotations

import html
import random
import re
from typing import List

import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

MAX_CHARS_PER_PAGE = 12000
TIMEOUT_SECONDS = 12
NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form")


class WebScraper:
    def fetch_text(self, url: str) -> str:
        if not url or not url.startswith("http"):
            return ""
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=TIMEOUT_SECONDS,
            )
            content_type = resp.headers.get("Content-Type", "")
            if resp.status_code != 200 or "text/html" not in content_type:
                return ""
            return self._extract_text(resp.text)
        except Exception:
            return ""

    @staticmethod
    def _extract_text(html_text: str) -> str:
        soup = BeautifulSoup(html_text, "lxml")
        for tag in soup(NOISE_TAGS):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"})
        root = main or soup.body or soup

        chunks: List[str] = []
        for p in root.find_all("p"):
            text = re.sub(r"\s+", " ", p.get_text(separator=" ", strip=True))
            if len(text) > 30:
                chunks.append(text)

        text = html.unescape("\n\n".join(chunks))
        return text[:MAX_CHARS_PER_PAGE].strip()
