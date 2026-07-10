# 🔍 AI Web Research Assistant

A fully functional Python AI assistant that:

1. **Searches Wikipedia** for a reliable summary.
2. **Searches the web** via DuckDuckGo (a Google alternative that works without API keys).
3. **Scrapes the top web pages** and extracts readable text.
4. **Synthesizes a cited answer** using OpenAI (optional) or a local extractive summarizer.

It works out of the box with free tools, and you can optionally plug in your OpenAI API key for more natural, human-like answers.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `ai_researcher.py` | Core engine: search, scrape, summarize |
| `cli.py` | Command-line interface |
| `app.py` | Streamlit web interface |
| `requirements.txt` | Python dependencies |
| `.env.example` | Example environment variables |
| `example.py` | Programmatic usage example |
| `api.py` | FastAPI REST API |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Add an OpenAI API key

Copy the example file and add your key:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-3.5-turbo
```

> Without an OpenAI key, the assistant still works using a local extractive summary.

### 3. (Optional) Add a SerpAPI key for real Google results

By default the assistant uses **DuckDuckGo** (free, no key). To get results from the real Google search engine, add a [SerpAPI](https://serpapi.com/) key to `.env`:

```env
SERPAPI_API_KEY=your-serpapi-key-here
```

---

## 💻 Usage

### Command Line

```bash
python cli.py "What is photosynthesis?"
```

Show all sources:

```bash
python cli.py "What is photosynthesis?" --show-sources --show-wiki
```

Scrape more web pages:

```bash
python cli.py "latest Mars rover discoveries" --web-results 6
```

### Web Interface

```bash
streamlit run app.py
```

Then open your browser at `http://localhost:8501`.

### REST API

```bash
uvicorn api:app --reload --port 8000
```

Example request:

```bash
curl -X POST http://localhost:8000/research \
     -H "Content-Type: application/json" \
     -d '{"query": "What is quantum computing?"}'
```

---

## 🔧 How It Works

```
User Query
    │
    ├──► Wikipedia API ──► summary + URL
    │
    ├──► DuckDuckGo Search ──► top web links
    │
    └──► Web Scraper ──► readable text from each link
                │
                ▼
        Summarizer (OpenAI or local)
                │
                ▼
        Cited, synthesized answer
```

---

## ⚙️ Architecture

- **`SearchEngine`** — talks to `wikipedia`, `ddgs` (DuckDuckGo), and optionally SerpAPI (Google).
- **`WebScraper`** — fetches pages with `requests` and extracts text with `BeautifulSoup`.
- **`Summarizer`** — uses OpenAI when available; otherwise scores sentences for relevance.
- **`ResearchAssistant`** — orchestrates the pipeline and returns a structured result.

---

## 🛡️ Notes

- Web scraping respects common HTML structure (`<main>`, `<article>`, `<p>`).
- Some sites may block automated requests; those pages are skipped gracefully.
- DuckDuckGo search is used because it does not require an API key.
- For real Google search results, you can integrate **SerpAPI** or **Google Custom Search JSON API** by extending `SearchEngine`.

---

## 🧪 Example Output

```text
==============================================================
                         🤖 ANSWER
==============================================================
Photosynthesis is the process used by plants, algae, and some
bacteria to convert light energy into chemical energy stored in
glucose. It generally takes place in the chloroplasts and uses
water, carbon dioxide, and sunlight to produce oxygen and sugars.

Note: Set OPENAI_API_KEY for a more natural LLM-generated answer.
```

---

## 📜 License

MIT — free to use and modify.
