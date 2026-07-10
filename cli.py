#!/usr/bin/env python3
"""
Command-line interface for the AI Web Research Assistant.

Examples:
    python cli.py "What is photosynthesis?"
    python cli.py "latest Mars rover discoveries" --web-results 6
"""

from __future__ import annotations

import argparse
import textwrap
from ai_researcher import ResearchAssistant


def print_box(title: str, body: str, width: int = 78) -> None:
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)
    print(textwrap.fill(body, width=width))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Web Research Assistant — search Wikipedia & the web."
    )
    parser.add_argument("query", help="Your research question.")
    parser.add_argument(
        "--web-results",
        type=int,
        default=4,
        help="Number of web pages to scrape (default: 4).",
    )
    parser.add_argument(
        "--show-sources",
        action="store_true",
        help="Display all discovered sources.",
    )
    parser.add_argument(
        "--show-wiki",
        action="store_true",
        help="Display the full Wikipedia summary.",
    )
    args = parser.parse_args()

    assistant = ResearchAssistant(
        max_web_results=args.web_results,
        progress_callback=lambda msg: print(f"  → {msg}"),
    )

    print(f"\n🔍 Researching: {args.query}\n")
    result = assistant.research(args.query)

    print_box("🤖 ANSWER", result["answer"])

    if args.show_wiki and result["wikipedia_summary"]:
        print_box("📚 WIKIPEDIA SUMMARY", result["wikipedia_summary"])
        print(f"Wikipedia URL: {result['wikipedia_url']}")

    if args.show_sources:
        print("\n" + "-" * 78)
        print("🔗 SOURCES")
        print("-" * 78)
        for i, source in enumerate(result["sources"], start=1):
            print(f"\n{i}. {source['title']}")
            print(f"   URL: {source['url']}")
            print(f"   Snippet: {source['snippet'][:200]}...")

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
