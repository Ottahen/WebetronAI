"""
Turns gathered sources into one answer.

Three backends, tried in this order:
  1. OpenAI       -- if OPENAI_API_KEY is set. Most natural answers.
  2. t5-small      -- if SUMMARIZER_BACKEND=t5 and `transformers`/`torch`
                       are installed. Fully local, no API key, but a first
                       run downloads the ~240MB model from Hugging Face.
                       Off by default: it's a heavy optional dependency,
                       per the brief ("t5-small... MORE OPTIONAL").
  3. Local extractive -- always available, zero dependencies beyond the
                       standard library. Scores sentences by how many
                       query words they share and stitches the best ones
                       back together in their original order.
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple

from .connectors.base import Source

MAX_CONTEXT_CHARS_PER_SOURCE = 1200


class Summarizer:
    def __init__(self) -> None:
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.use_t5 = os.environ.get("SUMMARIZER_BACKEND", "").lower() == "t5"
        self._t5_pipeline = None  # lazy-loaded on first use

    def answer(
        self,
        query: str,
        sources: List[Source],
        scraped_texts: List[str],
        wiki_summary: str | None,
        allow_llm: bool = True,
    ) -> Tuple[str, str]:
        """Returns (answer_text, backend_used). Set allow_llm=False to force
        a local-only backend (t5/extractive) even if OPENAI_API_KEY is set."""
        context = self._build_context(sources, scraped_texts, wiki_summary)

        if self.openai_key and allow_llm:
            answer = self._openai_answer(query, context)
            if answer:
                return answer, "openai"

        if self.use_t5:
            answer = self._t5_answer(context)
            if answer:
                return answer, "t5-small"

        return self._extractive_answer(query, context), "extractive"

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(
        sources: List[Source], scraped_texts: List[str], wiki_summary: str | None
    ) -> str:
        parts: List[str] = []
        if wiki_summary:
            parts.append(f"[Wikipedia]\n{wiki_summary}")

        for i, source in enumerate(sources):
            block = f"[{source.provider}] {source.title}\n{source.snippet}"
            if i < len(scraped_texts) and scraped_texts[i]:
                block += "\n" + scraped_texts[i][:MAX_CONTEXT_CHARS_PER_SOURCE]
            parts.append(block)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Backend 1: OpenAI
    # ------------------------------------------------------------------

    def _openai_answer(self, query: str, context: str) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Clued, a research assistant. Answer using only the "
                            "provided context, citing sources by name where useful. If the "
                            "context is insufficient, say so plainly. Be concise but complete."
                        ),
                    },
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
                ],
                temperature=0.3,
                max_tokens=700,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Backend 2: local t5-small (optional, heavy)
    # ------------------------------------------------------------------

    def _t5_answer(self, context: str) -> str:
        try:
            if self._t5_pipeline is None:
                from transformers import pipeline
                self._t5_pipeline = pipeline("summarization", model="t5-small")

            # t5-small has a small input window; keep it modest.
            trimmed = context[:3000]
            if not trimmed.strip():
                return ""
            result = self._t5_pipeline(trimmed, max_length=180, min_length=40, do_sample=False)
            return result[0]["summary_text"].strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Backend 3: local extractive summary (always available)
    # ------------------------------------------------------------------

    def _extractive_answer(self, query: str, context: str) -> str:
        sentences = self._split_sentences(context)
        if not sentences:
            return "No usable content was found to answer this question."

        query_words = self._tokenize(query)
        ranked = sorted(
            range(len(sentences)),
            key=lambda i: self._score(sentences[i], query_words),
            reverse=True,
        )
        top_indices = sorted(ranked[: min(6, len(ranked))])
        summary = " ".join(sentences[i] for i in top_indices)
        return summary[:2200]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
        return [
            s.strip()
            for s in raw
            if len(s.strip()) >= 25 and "[" not in s[:2] and s.count("http") == 0
        ]

    @staticmethod
    def _tokenize(text: str) -> set:
        return set(re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()))

    @classmethod
    def _score(cls, sentence: str, query_words: set) -> float:
        tokens = cls._tokenize(sentence)
        if not tokens:
            return 0.0
        overlap = len(tokens & query_words)
        length_bonus = min(len(tokens) / 25.0, 1.5)
        return overlap * 2 + length_bonus
