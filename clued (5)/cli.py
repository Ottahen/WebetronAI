#!/usr/bin/env python3
"""
Command-line interface for Clued.

Examples:
    python cli.py "What is photosynthesis?"
    python cli.py "latest ozempic clinical trials" --show-sources
    python cli.py "US inflation rate" --show-sources
"""

from __future__ import annotations

import argparse
import textwrap

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from clued_assistant import ClueEngine


def print_box(title: str, body: str, width: int = 78) -> None:
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)
    print(textwrap.fill(body, width=width))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clued — a multi-source AI research assistant."
    )
    parser.add_argument("query", help="Your research question.")
    parser.add_argument(
        "--show-sources", action="store_true", help="List every source found."
    )
    args = parser.parse_args()

    engine = ClueEngine(progress_callback=lambda msg: print(f"  → {msg}"))

    print(f"\n🔍 Researching: {args.query}\n")
    result = engine.research(args.query)

    print(f"\nDomains detected: {', '.join(result['domains'])}")
    print_box(f"🤖 ANSWER ({result['answer_backend']})", result["answer"])

    if result["wikipedia_summary"]:
        print_box("📚 WIKIPEDIA", result["wikipedia_summary"])

    for note in result["warnings"]:
        print(f"\n💡 {note}")

    if args.show_sources:
        print("\n" + "-" * 78)
        print("🔗 SOURCES")
        print("-" * 78)
        for i, source in enumerate(result["sources"], start=1):
            print(f"\n{i}. [{source['provider']}] {source['title']}")
            print(f"   {source['url']}")
            if source["snippet"]:
                print(f"   {source['snippet'][:200]}")

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
