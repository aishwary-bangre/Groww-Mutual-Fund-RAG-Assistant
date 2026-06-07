"""
engine.py — RAG Query Engine

Phase 5 pipeline:
  1. PII sanitization      — block queries with personal data
  2. Intent classification — refuse advisory queries
  3. Fund name detection   — add metadata filter if a fund is named
  4. Vector retrieval      — top-K chunks from ChromaDB
  5. Distance threshold    — detect out-of-scope queries
  6. LLM answer generation — strict 3-sentence Gemini response
  7. Structured response   — answer + citation_url + last_updated
"""

import re
import sys
sys.path.insert(0, "backend")

from guardrails import sanitize_pii, classify_intent, build_refusal, INTENT_ADVISORY
from vector_db import query_vector_db
from config import (
    GEMINI_API_KEY, GEMINI_LLM_MODEL,
    DISTANCE_THRESHOLD, RETRIEVAL_TOP_K, CORPUS_URLS
)

# ──────────────────────────────────────────────────────────────────────────────
# Fund Name Detection
# ──────────────────────────────────────────────────────────────────────────────

# Full scheme names from config
FUND_NAMES: list[str] = [entry["scheme_name"] for entry in CORPUS_URLS]

# Short aliases → full scheme_name (order matters: more specific first)
FUND_ALIASES: dict[str, str] = {
    "hdfc silver etf":          "HDFC Silver ETF FOF Direct Growth",
    "hdfc silver":              "HDFC Silver ETF FOF Direct Growth",
    "silver etf":               "HDFC Silver ETF FOF Direct Growth",
    "parag parikh long term":   "Parag Parikh Long Term Value Fund Direct Growth",
    "parag parikh":             "Parag Parikh Long Term Value Fund Direct Growth",
    "ppfas":                    "Parag Parikh Long Term Value Fund Direct Growth",
    "hdfc mid cap":             "HDFC Mid Cap Fund Direct Growth",
    "hdfc midcap":              "HDFC Mid Cap Fund Direct Growth",
    "hdfc equity":              "HDFC Equity Fund Direct Growth",
    "motilal oswal midcap":     "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
    "motilal oswal focused":    "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
    "motilal oswal":            "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
    "motilal":                  "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
    "focused midcap":           "Motilal Oswal Focused Midcap 30 Fund Direct Growth",
}


def detect_fund_name(query: str) -> str | None:
    """
    Scans the query for a known fund name or alias.
    Returns the full scheme_name if found, else None.
    Full names are checked before aliases to avoid false matches.
    """
    q = query.lower()

    # Check full scheme names first (exact match within query)
    for name in FUND_NAMES:
        if name.lower() in q:
            return name

    # Check aliases (longer aliases first to avoid premature short matches)
    for alias in sorted(FUND_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", q):
            return FUND_ALIASES[alias]

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Gemini LLM Prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a factual assistant for mutual fund information. "
    "Answer the user's question using ONLY the provided context. "
    "Rules:\n"
    "- Answer in MAXIMUM 3 sentences.\n"
    "- Cite specific numbers or facts from the context.\n"
    "- Do NOT give investment advice, recommendations, or opinions.\n"
    "- If the answer is not in the context, respond with: "
    "  'I don't have that information in my knowledge base.'\n"
    "- Do NOT make up any facts."
)

OUT_OF_SCOPE_MSG = (
    "I don't have information about that in my knowledge base. "
    "I can only answer questions about the 5 mutual fund schemes I have data for: "
    "HDFC Silver ETF FOF, Parag Parikh Long Term Value, HDFC Mid Cap, "
    "HDFC Equity, and Motilal Oswal Focused Midcap 30."
)


# ──────────────────────────────────────────────────────────────────────────────
# Main Engine Function
# ──────────────────────────────────────────────────────────────────────────────

def answer_query(query: str) -> dict:
    """
    Full RAG pipeline for a single user query.

    Returns:
        {
            answer:       str   — the LLM-generated or refusal response
            citation_url: str   — source Groww URL (from top retrieved chunk)
            last_updated: str   — scrape date of the data (YYYY-MM-DD)
            intent:       str   — FACTUAL | ADVISORY | BLOCKED_PII | OUT_OF_SCOPE
        }
    """
    from google import genai

    # ── Step 1: PII check ──────────────────────────────────────────────────
    pii_result = sanitize_pii(query)
    if not pii_result["is_clean"]:
        return {
            "answer":       pii_result["response"],
            "citation_url": None,
            "last_updated": None,
            "intent":       "BLOCKED_PII",
        }

    # ── Step 2: Intent classification ──────────────────────────────────────
    intent_result = classify_intent(query)
    if intent_result["intent"] == INTENT_ADVISORY:
        refusal = build_refusal("advisory")
        return {**refusal, "intent": "ADVISORY"}

    # ── Step 3: Fund name detection ────────────────────────────────────────
    detected_fund = detect_fund_name(query)

    # ── Step 4: Vector retrieval ───────────────────────────────────────────
    try:
        chunks = query_vector_db(
            query_text=query,
            top_k=RETRIEVAL_TOP_K,
            fund_filter=detected_fund
        )
    except Exception as e:
        return {
            "answer":       f"Retrieval error: {e}",
            "citation_url": None,
            "last_updated": None,
            "intent":       "ERROR",
        }

    # ── Step 5: Distance threshold check ──────────────────────────────────
    if not chunks or chunks[0]["distance"] > DISTANCE_THRESHOLD:
        return {
            "answer":       OUT_OF_SCOPE_MSG,
            "citation_url": None,
            "last_updated": None,
            "intent":       "OUT_OF_SCOPE",
        }

    # ── Step 6: Build prompt and call Gemini LLM ───────────────────────────
    context = "\n\n---\n\n".join(chunk["text"] for chunk in chunks)

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_LLM_MODEL,
        contents=prompt
    )

    answer_text = (
        response.text.strip()
        if response.text
        else "I don't have that information in my knowledge base."
    )

    # ── Step 7: Build structured response ─────────────────────────────────
    best_meta = chunks[0]["metadata"]
    return {
        "answer":       answer_text,
        "citation_url": best_meta.get("url", ""),
        "last_updated": best_meta.get("scraped_at", ""),
        "intent":       "FACTUAL",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Self-test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    test_cases = [
        # (query, expected_intent)
        ("What is the exit load of HDFC Mid Cap Fund?",        "FACTUAL"),
        ("Who manages Parag Parikh Long Term Value Fund?",      "FACTUAL"),
        ("What is the minimum SIP for Motilal Oswal?",         "FACTUAL"),
        ("Should I invest in HDFC Equity Fund?",               "ADVISORY"),
        ("My PAN is ABCDE1234F, which fund should I buy?",     "BLOCKED_PII"),
        ("What is the weather like today?",                     "OUT_OF_SCOPE"),
    ]

    print("=" * 65)
    print("PHASE 5 ENGINE SELF-TEST")
    print("=" * 65)

    for query, expected in test_cases:
        print(f"\nQ: {query}")
        result = answer_query(query)
        intent = result["intent"]
        status = "PASS" if intent == expected else "FAIL"
        print(f"[{status}] Intent: {intent} (expected: {expected})")
        if intent == "FACTUAL":
            print(f"  Answer: {result['answer'][:150]}...")
            print(f"  Source: {result['citation_url']}")
            print(f"  Updated: {result['last_updated']}")
        else:
            print(f"  Response: {result['answer'][:120]}...")
