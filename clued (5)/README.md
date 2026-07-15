# 🌤️ Clued

**Clued**, by **PrimeAct** (open GitHub org, github.com/PrimeAct) — created by ℒ / Ottahen
(github.com/Ottahen).

A Python AI assistant with three modes, picked from the dropdown in the chat box:

| Mode | What it does |
|---|---|
| **Webetron** | The original pipeline: classifies your question, fans out to every relevant live data source in parallel, scrapes the top web pages, summarizes. |
| **Open** | Same pipeline, narrowed to three health sources — PubMed Central, ClinicalTrials.gov, OpenFDA — plus the web/Wikipedia baseline. Deliberately stays on the local summarizer even if `OPENAI_API_KEY` is set, so it always works with zero keys. |
| **Atlas** | Free-form, multi-turn chat with memory, image understanding (upload an image and ask about it), and image generation (2 images/request, credited to Perchance — see below), rendered with real Markdown and LaTeX. |

If you ask Clued what it is or who made it, it answers directly with that identity — this
is the one scripted response in the app; every other answer is generated from real sources.

---

## How Webetron/Open decide which sources to use

```
your question
      │
      ▼
 router.classify()  →  {health, finance, academic, geospatial, ...}
      │
      ▼
 modes.py filters connectors by mode, then runs every connector whose
 domain matches the query (in parallel, each wrapped so one failing
 API can't take down the request)
      │
      ▼
 scrape full text for the top general web results
      │
      ▼
 Summarizer: OpenAI (if key set, and mode allows it) → t5-small (if
 enabled) → local extractive fallback (always available)
      │
      ▼
 one answer + a grouped, cited source list
```

## Atlas mode, honestly

Atlas keeps a server-side conversation per session (in-process — restarting the server
clears it; add a real datastore if you need chats to survive restarts) and:

- **With `OPENAI_API_KEY` set**: genuine open-domain chat, including looking at an
  uploaded image, using the full conversation history each turn.
- **Without a key**: Atlas still remembers what you said earlier in the session, but each
  reply is produced by running your message through Webetron's research pipeline plus the
  local extractive summarizer. It's useful, but it is *not* a general chatbot — the UI says
  so on every fallback reply rather than pretending otherwise. `t5-small` alone is a
  summarization model, not a conversational one, so it's used the same way here as
  elsewhere: to condense retrieved text, not to hold a free-form conversation.

**Image generation** calls **[Perchance's AI Text-to-Image Generator](https://perchance.org/ai-text-to-image-generator)**
and always credits Perchance in the response — Clued has no image model of its own.
Perchance doesn't publish an official REST API, so `clued_assistant/imagegen.py` talks to
the same endpoints its own web page uses, the way several open-source "perchance API"
wrappers on GitHub do. That means it can break without notice if Perchance changes
something; when it does, Clued fails with a clear error rather than faking a result.

## What's implemented, and what isn't

**Implemented as live, query-time connectors** (`clued_assistant/connectors/`):

| Source | Domain | Notes |
|---|---|---|
| DuckDuckGo / Google | general | Google via `SERPAPI_API_KEY` if set, else DuckDuckGo (no key) |
| Wikipedia | general | encyclopedia summary + link |
| arXiv | academic | public Atom API, no key |
| OpenAlex | academic | free API key recommended (required as of Feb 2026 for full access) |
| PubMed Central | health | NCBI E-utilities, no key required |
| ClinicalTrials.gov | health | official v2 REST API, no key |
| OpenFDA | health | drug label data, no key required |
| SEC EDGAR | finance | full-text filing search, no key |
| World Bank | finance | curated set of common macro indicators/countries |
| FRED | finance | **requires** a free API key — no keyless tier exists |
| OpenStreetMap (Nominatim) | geospatial | geocoding, identifying User-Agent required |
| Perchance (image gen) | atlas only | unofficial, best-effort — see caveat above |

**Deliberately not implemented**, with the reason, so nothing pretends to work when it can't:

- **NASA EarthData / Copernicus** — both gate *downloads and API access* behind an account
  login (Earthdata Login / Copernicus Data Space credentials). You can browse and search
  without an account, but Clued won't scrape around that login wall — that's circumventing
  the access control the data owner put there on purpose. If you have your own credentials,
  it's a small job to add an authenticated connector for either.
- **CDC WONDER** — no public JSON/REST API; it's a web query tool without a documented
  programmatic endpoint.
- **IMF** — has a real but SDMX-based data API that's changed shape several times; left out
  rather than shipping something likely to break on you. World Bank covers most of the same
  macro indicators.
- **COCO, Open Images, Mozilla Data Collective, Bhashini, OpenCorpus, Webhose, inAI-wiki** —
  bulk *dataset downloads* for training models, not live search/query APIs. There's no "ask
  a question, get an answer" endpoint to wire up.

Every connector follows the same `Connector` base class (`connectors/base.py`), so adding a
real source later is a matter of writing one small file and adding it to
`connectors/__init__.py`.

## Text-to-speech & voice input

The UI uses **[VoiPi](https://github.com/pithings/voipi)**'s browser provider (loaded from
`esm.sh`, no install step) to read answers aloud, falling back to the native
`speechSynthesis` API if the CDN import fails. Voice *input* (the mic button) uses the
browser's own `SpeechRecognition` API.

## Optional local summarizer (t5-small)

By default, answers use a small dependency-free extractive summarizer, or OpenAI if you set
`OPENAI_API_KEY`. To run summarization fully locally and offline instead, set
`SUMMARIZER_BACKEND=t5` and install the (heavy, ~2GB with PyTorch) optional dependencies:

```bash
pip install transformers torch
```

---

## 📁 Files

| File | Purpose |
|---|---|
| `clued_assistant/core.py` | `ClueEngine` — the Webetron/Open orchestrator |
| `clued_assistant/modes.py` | the three modes and which connectors each is allowed to use |
| `clued_assistant/chat.py` | `AtlasChat` — session memory, LLM chat, research fallback |
| `clued_assistant/imagegen.py` | Perchance-backed image generation for Atlas |
| `clued_assistant/identity.py` | "what's your name" / "who made you" answers |
| `clued_assistant/router.py` | query → domain classifier |
| `clued_assistant/scraper.py` | fetches + extracts readable text from a URL |
| `clued_assistant/summarizer.py` | OpenAI / t5-small / extractive answer generation |
| `clued_assistant/connectors/` | one file per data source |
| `api.py` | FastAPI backend + serves the web UI |
| `static/` | the Clued UI (HTML/CSS/JS, chat thread, VoiPi TTS, voice input) |
| `cli.py` | command-line interface |
| `example.py` | programmatic usage example |

## 🚀 Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # optional — fill in any keys you have
uvicorn api:app --reload --port 8000
```

Open **http://localhost:8000** — no login beyond entering a display name, straight into chat.

### Command line

```bash
python cli.py "What is photosynthesis?"
python cli.py "latest ozempic clinical trials" --show-sources
python cli.py "US inflation rate" --show-sources
```

### Programmatically

```python
from clued_assistant import ClueEngine

engine = ClueEngine()
result = engine.research("What is quantum computing?", mode="webetron")
print(result["answer"])
```

## ⚙️ Environment variables

Everything is optional — Clued works with zero keys set. See `.env.example` for the full
list (OpenAI, OpenAlex, NCBI, FRED, SerpAPI, contact email). Any key you don't set simply
means that one connector or summarizer backend is skipped — the UI shows a small note when
a relevant one is missing (e.g. "Set FRED_API_KEY..." on a finance question).

## 🛡️ Notes

- Every connector fails independently and silently returns no results rather than breaking
  the whole request.
- Some government/scholarly APIs (SEC EDGAR, Nominatim) require an identifying `User-Agent`
  by policy; set `CONTACT_EMAIL` in `.env` so it's included automatically.
- Nominatim (OpenStreetMap) asks for roughly 1 request/second — fine for occasional
  geocoding, not for bulk lookups.
- Clued always discloses what it's built on — it doesn't claim third-party data or the
  Perchance-powered image generation as proprietary technology.

## 📜 License

MIT — free to use and modify.
