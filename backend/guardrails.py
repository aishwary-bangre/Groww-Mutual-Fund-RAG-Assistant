"""
guardrails.py — PII Sanitizer, Intent Classifier & Refusal Handler

Phase 4 components:
  1. sanitize_pii(query)    — Block/scrub queries containing sensitive personal data
  2. classify_intent(query) — Classify as FACTUAL or ADVISORY
  3. build_refusal(reason)  — Construct a compliant refusal response
"""

import re

# ──────────────────────────────────────────────────────────────────────────────
# 1. PII SANITIZER
# ──────────────────────────────────────────────────────────────────────────────

# PII regex patterns
PII_PATTERNS = {
    "PAN":          r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "Aadhaar":      r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    "Phone":        r"\b(?:\+91[\s\-]?)?[6-9]\d{9}\b",
    "Email":        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
    "Bank Account": r"\b\d{9,18}\b",
    "IFSC":         r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "OTP":          r"\b\d{4,8}\b",
}

def sanitize_pii(query: str) -> dict:
    """
    Scans the query for PII patterns.

    Returns:
        {
            "is_clean": bool,
            "detected": list of PII type names found,
            "response": str (refusal message if PII detected, else None)
        }
    """
    detected = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            detected.append(pii_type)

    if detected:
        return {
            "is_clean": False,
            "detected": detected,
            "response": (
                "⚠️ Your query appears to contain sensitive personal information "
                f"({', '.join(detected)}). For your security, please do not share "
                "personal financial data. Ask your question without including "
                "personal details."
            )
        }

    return {"is_clean": True, "detected": [], "response": None}


# ──────────────────────────────────────────────────────────────────────────────
# 2. INTENT CLASSIFIER
# ──────────────────────────────────────────────────────────────────────────────

# Keywords that strongly indicate advisory / subjective intent
ADVISORY_PATTERNS = [
    r"\bshould i\b",
    r"\bshould we\b",
    r"\bwould you recommend\b",
    r"\badvise\b",
    r"\badvice\b",
    r"\brecommend\b",
    r"\bbetter (?:fund|option|choice|investment)\b",
    r"\bbest (?:fund|option|choice|investment)\b",
    r"\bwhich (?:fund|scheme) (?:is|should)\b",
    r"\bworth (?:investing|buying)\b",
    r"\bshould .{0,30} invest\b",
    r"\bwill (?:it|the fund|this fund) (?:go up|rise|fall|perform)\b",
    r"\bgood investment\b",
    r"\bgood fund\b",
    r"\bcompare .{0,30} (?:fund|scheme)\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bbet(?:ter|st) performing\b",
    r"\bsafe(?:r|st)?\b",
    r"\brisky\b",
    r"\bright (?:fund|choice|time)\b",
    r"\btime to (?:buy|invest|sell)\b",
]

# Keywords that strongly indicate factual / objective intent
FACTUAL_PATTERNS = [
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bwhat'?s\b",
    r"\bhow much\b",
    r"\bhow many\b",
    r"\btell me about\b",
    r"\bexpense ratio\b",
    r"\bexit load\b",
    r"\bnav\b",
    r"\baum\b",
    r"\bfund size\b",
    r"\bminimum (?:sip|investment|amount)\b",
    r"\bsip (?:minimum|amount|date)\b",
    r"\bfund manager\b",
    r"\bbenchmark\b",
    r"\bcategory\b",
    r"\blaunch date\b",
    r"\bholdings\b",
    r"\breturn(?:s)?\b",
    r"\bperformance\b",
    r"\bisin\b",
    r"\block.?in\b",
    r"\btax\b",
    r"\bstamp duty\b",
    r"\bgroww rating\b",
]

INTENT_FACTUAL = "FACTUAL"
INTENT_ADVISORY = "ADVISORY"

def classify_intent(query: str) -> dict:
    """
    Classifies a query as FACTUAL or ADVISORY using pattern matching.

    Strategy:
    - Advisory patterns are checked first (stronger signal).
    - If any advisory pattern matches → ADVISORY.
    - If any factual pattern matches → FACTUAL.
    - Default fallback → FACTUAL (assume user wants facts).

    Returns:
        {
            "intent": "FACTUAL" | "ADVISORY",
            "matched_pattern": str (pattern that triggered classification)
        }
    """
    q = query.lower()

    for pattern in ADVISORY_PATTERNS:
        if re.search(pattern, q):
            return {"intent": INTENT_ADVISORY, "matched_pattern": pattern}

    for pattern in FACTUAL_PATTERNS:
        if re.search(pattern, q):
            return {"intent": INTENT_FACTUAL, "matched_pattern": pattern}

    # Default to FACTUAL — benefit of the doubt for ambiguous queries
    return {"intent": INTENT_FACTUAL, "matched_pattern": "default"}


# ──────────────────────────────────────────────────────────────────────────────
# 3. REFUSAL HANDLER
# ──────────────────────────────────────────────────────────────────────────────

AMFI_LINK = "https://www.amfiindia.com/investor-corner/knowledge-center"
SEBI_LINK = "https://investor.sebi.gov.in"

def build_refusal(reason: str = "advisory") -> dict:
    """
    Builds a compliant, polite refusal response.

    Args:
        reason: "advisory" | "out_of_scope"

    Returns:
        { "answer": str, "citation_url": str, "last_updated": None }
    """
    if reason == "advisory":
        answer = (
            "I can only provide factual information about mutual fund schemes — "
            "such as expense ratios, exit loads, NAV, and fund details. "
            "For investment advice, please consult a SEBI-registered financial advisor. "
            f"You can also learn more at AMFI Investor Education: {AMFI_LINK}"
        )
    else:
        answer = (
            "This question is outside the scope of what I can answer. "
            "I'm designed to provide factual details about specific mutual fund schemes. "
            f"For broader financial education, visit: {SEBI_LINK}"
        )

    return {
        "answer": answer,
        "citation_url": AMFI_LINK,
        "last_updated": None
    }


# ──────────────────────────────────────────────────────────────────────────────
# Self-test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_queries = [
        ("What is the exit load of HDFC Mid Cap Fund?",        "FACTUAL"),
        ("Should I invest in Parag Parikh Flexi Cap Fund?",    "ADVISORY"),
        ("Which fund is better, HDFC or Motilal?",             "ADVISORY"),
        ("What is the minimum SIP amount for HDFC Equity?",    "FACTUAL"),
        ("Tell me about the benchmark of HDFC Mid Cap Fund",   "FACTUAL"),
        ("Is HDFC Silver ETF a good investment?",              "ADVISORY"),
        ("What is the AUM of Parag Parikh Long Term Value?",   "FACTUAL"),
    ]

    pii_queries = [
        "My PAN is ABCDE1234F, what should I invest in?",
        "My phone is 9876543210 and I want to buy a fund",
        "What is the NAV today?",  # Clean
    ]

    print("=== INTENT CLASSIFICATION ===")
    all_pass = True
    for query, expected in test_queries:
        result = classify_intent(query)
        status = "PASS" if result["intent"] == expected else "FAIL"
        if result["intent"] != expected:
            all_pass = False
        print(f"[{status}] [{result['intent']}] {query}")

    print(f"\nAll correct: {all_pass}")

    print("\n=== PII DETECTION ===")
    for query in pii_queries:
        result = sanitize_pii(query)
        status = "[BLOCKED]" if not result["is_clean"] else "[CLEAN]  "
        print(f"{status} {query[:60]}")
        if not result["is_clean"]:
            print(f"  Detected: {result['detected']}")
