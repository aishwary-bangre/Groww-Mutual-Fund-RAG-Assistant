import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Authentication ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    print("WARNING: GEMINI_API_KEY not set in .env file.")

# ── Gemini Model Configuration ───────────────────────────────────────────────
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL",   "models/gemini-embedding-001")
GEMINI_LLM_MODEL  = os.getenv("GEMINI_LLM_MODEL",  "gemini-2.5-flash")

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).resolve().parent.parent
DATA_DIR          = BASE_DIR / "data"
VECTOR_STORE_DIR  = BASE_DIR / os.getenv("VECTOR_STORE_PATH", "data/vector_store")

# Ensure directories exist
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# ── Vector Database Configuration ────────────────────────────────────────────
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION",  "mutual_funds")
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "0.45"))
RETRIEVAL_TOP_K    = int(os.getenv("RETRIEVAL_TOP_K",    "3"))

# ── Scheduler Configuration ───────────────────────────────────────────────────
REFRESH_TIME = os.getenv("REFRESH_TIME", "00:00")  # HH:MM daily refresh

# ── Backend Server Configuration ─────────────────────────────────────────────
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# ── Scraper request headers (browser-like to avoid bot blocks) ────────────────
SCRAPER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ── Corpus: 5 Groww mutual fund scheme URLs ───────────────────────────────────
CORPUS_URLS = [
    {
        "scheme_name": "HDFC Silver ETF FOF Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
        "doc_type": "scheme-page",
    },
    {
        "scheme_name": "Parag Parikh Long Term Value Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth",
        "doc_type": "scheme-page",
    },
    {
        "scheme_name": "HDFC Mid Cap Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "doc_type": "scheme-page",
    },
    {
        "scheme_name": "HDFC Equity Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "doc_type": "scheme-page",
    },
    {
        "scheme_name": "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/motilal-oswal-most-focused-midcap-30-fund-direct-growth",
        "doc_type": "scheme-page",
    },
]
