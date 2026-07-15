"""
Example: using Clued programmatically.
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from clued_assistant import ClueEngine

engine = ClueEngine(progress_callback=print)

result = engine.research("What are the health benefits of green tea?")

print("\n--- DOMAINS ---")
print(result["domains"])

print("\n--- ANSWER ---")
print(result["answer"])

print("\n--- SOURCES ---")
for source in result["sources"]:
    print(f"- [{source['provider']}] {source['title']}: {source['url']}")
