"""
Example: using the AI Web Research Assistant programmatically.
"""

from ai_researcher import ResearchAssistant

assistant = ResearchAssistant(
    max_web_results=4,
    progress_callback=print,
)

result = assistant.research("What are the health benefits of green tea?")

print("\n--- ANSWER ---")
print(result["answer"])

print("\n--- WIKIPEDIA URL ---")
print(result["wikipedia_url"])

print("\n--- SOURCES ---")
for source in result["sources"]:
    print(f"- {source['title']}: {source['url']}")
