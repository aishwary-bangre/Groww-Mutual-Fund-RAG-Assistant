# Groww Mutual Fund RAG Assistant - Implementation Plan

This document details the phase-wise implementation strategy, aligned with [Architecture.md](file:///d:/cursor%20projects/Groww%20Mutual%20Fund%20RAG%20Assistant/Architecture.md).

---

## 1. Project Directory Structure

```text
groww-rag-assistant/
├── backend/
│   ├── config.py           # Source URLs, directories, scraper headers, constants
│   ├── parser.py           # Groww scraper: fetch HTML → extract __NEXT_DATA__ JSON → format text
│   ├── vector_db.py        # Chunker + Gemini embedding + ChromaDB storage & retrieval
│   ├── guardrails.py       # PII scrubber, intent classifier, refusal handler
│   ├── scheduler.py        # Daily refresh: re-scrape → re-embed → upsert ChromaDB
│   ├── engine.py           # RAG orchestrator: guardrails → retrieval → LLM → response
│   └── app.py              # FastAPI server exposing /chat endpoint
├── frontend/
│   ├── index.html          # Chat interface
│   ├── style.css           # Premium Groww-inspired styling
│   └── app.js              # Frontend logic
├── data/
│   ├── cleaned_funds.json  # Cached clean fund data (re-generated on demand)
│   └── vector_store/       # Persistent ChromaDB database files
├── run_embeddings.py       # One-shot pipeline: scrape → chunk → embed → store
├── test_query.py           # Diagnostic: chunk inspection + retrieval quality tests
├── pyrightconfig.json      # Language server config (venv + extraPaths)
├── .env                    # GEMINI_API_KEY, HOST, PORT
├── .env.example            # Environment variable template
├── requirements.txt        # Backend dependencies
└── README.md               # Setup and run instructions
```

> [!NOTE]
> There is no `raw_documents/` folder. Data is scraped live from Groww's public fund pages — no local PDF storage.

---

## 2. Phase-Wise Roadmap

### Phase 1: Environment Setup ✅
1. Initialized project directory structure.
2. Installed dependencies into `.venv` (Python 3.12.10):
   * `fastapi`, `uvicorn`, `pydantic` — Backend API
   * `google-genai>=2.8.0` — Gemini LLM + Embedding API (new SDK supporting `AQ.` keys)
   * `chromadb>=0.6.0` — Local vector database (NumPy 2.0 compatible)
   * `requests`, `beautifulsoup4`, `lxml` — Web scraping
   * `python-dotenv` — Environment variable management
3. Set up `.env` with `GEMINI_API_KEY` (Google AI Studio `AQ.` format key).
4. Created Python 3.12 virtual environment (`.venv`) at project root.
5. Created `pyrightconfig.json` to fix language server import resolution.

---

### Phase 2: Web Scraping & Data Extraction ✅
**Files:** `backend/config.py`, `backend/parser.py`

#### Key Discovery
Groww uses **Next.js with SSR (Server-Side Rendering)**. All fund data is embedded in the page HTML inside a `<script id="__NEXT_DATA__">` JSON tag. We extract this JSON directly — no fragile HTML scraping needed.

#### 5 Fund URLs Configured in `config.py`
| Scheme Name | URL |
|---|---|
| HDFC Silver ETF FOF Direct Growth | `groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth` |
| Parag Parikh Long Term Value Fund Direct Growth | `groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth` |
| HDFC Mid Cap Fund Direct Growth | `groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |
| HDFC Equity Fund Direct Growth | `groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| Motilal Oswal Focused Midcap 30 Fund Direct Growth | `groww.in/mutual-funds/motilal-oswal-most-focused-midcap-30-fund-direct-growth` |

#### `parser.py` Pipeline
1. **`fetch_page(url)`** — HTTP GET with browser-like headers, returns raw HTML.
2. **`extract_next_data(html)`** — Regex extracts and parses the `__NEXT_DATA__` JSON blob (handles extra `nonce`/`crossorigin` attributes on the script tag).
3. **`format_fund_document(mf_data, url)`** — Converts `mfServerSideData` dict into a clean, multi-section text document with 9 labelled sections:
   - `=== FUND IDENTITY ===`
   - `=== FUND DESCRIPTION ===`
   - `=== KEY FACTS ===`
   - `=== INVESTMENT DETAILS ===`
   - `=== FUND MANAGER ===`
   - `=== RETURNS (ABSOLUTE) ===`
   - `=== RETURNS (SIP / XIRR) ===`
   - `=== TOP HOLDINGS ===`
   - `=== TAX INFORMATION ===`
4. **`load_all_documents()`** — Returns a list of documents. Each document has:
   - `cleaned_text`: Free-text document for chunking & embedding
   - `scheme_metadata`: **25 structured fields** for ChromaDB filters & UI display

#### `scheme_metadata` Structure (25 fields)
```json
{
  "scheme_name": "...",         "url": "...",
  "doc_type": "scheme-page",   "scraped_at": "YYYY-MM-DD",
  "isin": "...",                "fund_house": "...",
  "category": "Equity",        "sub_category": "Mid Cap",
  "plan_type": "Direct",       "launch_date": "...",
  "nav": 220.327,              "nav_date": "05-Jun-2026",
  "aum_crores": 94744.72,      "expense_ratio_pct": "0.73",
  "exit_load": "...",          "benchmark": "...",
  "groww_rating": 5,           "lock_in": "No lock-in",
  "min_sip_amount": 100,       "min_lumpsum_amount": 100,
  "fund_managers": "...",
  "return_1y_pct": 6.97,       "return_3y_pct": 84.73,   "return_5y_pct": 159.31,
  "sip_return_1y_pct": 3.07,   "sip_return_3y_pct": 11.39, "sip_return_5y_pct": 18.64
}
```

> [!NOTE]
> `cleaned_text` is used for semantic retrieval. `scheme_metadata` is used for ChromaDB filters, direct UI display, and citation footers — without needing LLM inference.

**Output cached to:** `data/cleaned_funds.json`

---

### Phase 3: Chunking, Embedding & Vector Storage ✅
**File:** `backend/vector_db.py`

#### Task 1 — `chunk_by_sections()` ✅
- Split each fund document on `=== ... ===` section headers → **9 chunks per fund × 5 funds = 45 total chunks**
- The `=== FUND IDENTITY ===` block is prepended to every non-identity chunk (self-contained context)
- Chunk sizes: Min 265 chars, Max 859 chars, Avg 471 chars

> **Why section-based instead of sliding window?**
> Our documents are pre-structured into 9 labelled sections. A sliding window would blindly split across boundaries. Section-based chunking ensures every chunk is a complete, meaningful unit — and retrieval tests confirmed each query retrieves the right section.

#### Task 2 — `generate_embeddings()` ✅
- Model: **`models/gemini-embedding-001`** via `google-genai` SDK (3072 dimensions)
- Rate limiting: 1.5s delay between calls + 3-attempt exponential backoff (10s, 20s) on 429 errors
- Result: **45/45 chunks embedded successfully**

#### Task 3 — `build_vector_store()` ✅
- ChromaDB 1.5.9 (NumPy 2.0 compatible), persistent at `data/vector_store/`
- Collection: `mutual_funds`, cosine similarity space
- Metadata sanitised to `str/int/float/bool` (ChromaDB requirement)
- **45 documents upserted and confirmed**

#### Task 4 — `query_vector_db()` ✅
- Query embedded with `task_type=RETRIEVAL_QUERY`
- Returns top-K chunks with `{ text, metadata, distance }`
- **Retrieval strategy:** Fund-name detection → `where` metadata filter if fund name found in query, distance threshold 0.45 for out-of-scope detection

#### Retrieval Quality (from `test_query.py` diagnostic)
| Query type | Accuracy | Distance range |
|---|---|---|
| Named fund + specific fact | 3/3 results correct | 0.18 – 0.30 |
| Named fund + generic question | 2/3 correct (1 cross-fund) | 0.23 – 0.26 |
| No fund name (generic) | Right sections, mixed funds (expected) | 0.35 – 0.38 |

---

### Phase 4: Intent Classification & Guardrails ✅
**File:** `backend/guardrails.py`

1. **`sanitize_pii(query)`** — Regex patterns for PAN, Aadhaar, Phone, Email, Bank Account, IFSC, OTP. Returns `{ is_clean, detected, response }`.
2. **`classify_intent(query)`** — Pure regex pattern matching (no Gemini call needed). Advisory patterns checked first. Returns `FACTUAL` or `ADVISORY`. **7/7 test cases passing.**
3. **`build_refusal(reason)`** — Returns a polite, compliant refusal with AMFI/SEBI educational links.

---

### Phase 5: RAG Query Engine ✅
**File:** `backend/engine.py`

1. Query → `sanitize_pii()` → if blocked, return PII refusal.
2. `classify_intent()` → if `ADVISORY`, return `build_refusal("advisory")`.
3. Extract fund name from query (match against known scheme names).
4. `query_vector_db(query, top_k=3, fund_filter=detected_fund)` → top-3 chunks.
5. Distance check: if best distance > 0.45 → return "I don't have information about this."
6. Build strict Gemini prompt → LLM response (3-sentence hard cap).
7. Return `{ answer, citation_url, last_updated }` from chunk metadata.

---

### Phase 6: FastAPI Backend ✅
**File:** `backend/app.py`

1. `POST /chat` — accepts `{ query: string }`, returns `{ answer, citation_url, last_updated }`.
2. `GET /health` — returns server + last refresh timestamp.
3. CORS enabled for local frontend.
4. Starts daily scheduler in `lifespan` event on server boot.

---

### Phase 7: User Interface ✅
**Files:** React SPA in `frontend/src/*` (React + Vite + Tailwind CSS)

1. **Brand Theme Integration**: Premium space-grade dark mode (`#0f131c` background, `#111827` elevated surfaces) with Groww primary green (`#00D09C`) and glassmorphic card layouts.
2. **Side Panel Session Manager**: Large "New Chat" button, lists renamable/deletable sessions persisted via browser `localStorage`.
3. **Chat Workspace Area**: Greeting banner, compliance disclaimer alerts, click-to-query suggestion cards, responsive toggle sidebar.
4. **Interactive Message Bubbles**: Custom regex text-formatting (translates bold `**text**` and bullets to clean HTML elements), typing loader animations, and citation pills linked back to scraping page URLs.
5. **Backend Health Sync**: Live header ping checking connection to Python server `http://127.0.0.1:8000/health`.

---

### Phase 8: Daily Data Refresh Scheduler ✅
**File:** `backend/scheduler.py`

NAV, AUM, and fund returns change **every trading day**. The vector store must stay fresh.

#### Strategy
- Uses a **zero-dependency background daemon thread** (implemented with Python standard `threading`, `time`, and `datetime` libraries) to guarantee reliability and ease of deployment.
- Runs as a background thread inside the FastAPI app startup (`lifespan` event) using `start_scheduler()`.
- Scheduled time: configurable via `REFRESH_TIME` in `.env` (defaults to `00:00` daily).
- **API Token Savings Check**: Integrates a SHA-256 hash validation mechanism. When scraping, it fetches existing records from ChromaDB, hashes each chunk, and only calls the Gemini Embedding API for chunks that have changed.
- **Index Order Preservation**: Performs in-place mutation of the original chunks array to guarantee index-stable ID generation and ensure a 100% caching hit rate for subsequent runs.

---

### Phase 9: Verification & Testing ✅
1. **Factual Queries**: Verified that query inputs retrieve the targeted sections, are restricted to a 3-sentence response, and render correct Groww citation pills with scraping dates.
2. **Advisory Interception**: Verified that queries with advisory intent (e.g., *"should I invest"*) are intercepted and refused with compliance disclaimers and AMFI education links without invoking LLM tokens.
3. **PII Interception**: Verified that personal inputs (e.g. containing a PAN) are scrubbed and refused automatically.
4. **Out-of-Scope Detection**: Verified that unrelated queries (e.g. weather) with cosine distance > `0.45` are safely refused.
5. **Daily Scheduler Validation**: Executed manual tests confirming that the SHA-256 cache hits and reuses 45/45 embeddings with zero API calls.
6. **UI Responsiveness & Delivery**: Opened the website in the browser directly using [index.html](file:///d:/cursor%20projects/Groww%20Mutual%20Fund%20RAG%20Assistant/index.html) and confirmed it works seamlessly with the running Python backend.
