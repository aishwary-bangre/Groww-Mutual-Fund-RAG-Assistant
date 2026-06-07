"""
Diagnostic script to understand chunk structure, embedding quality,
and retrieval behavior before designing the Phase 5 engine strategy.
"""
import sys
from collections import defaultdict
sys.path.insert(0, 'backend')
import chromadb
from config import VECTOR_STORE_DIR
from vector_db import query_vector_db

# ── 1. Inspect all chunks in ChromaDB ──────────────────────────────────────
chroma = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
col = chroma.get_collection("mutual_funds")

all_data = col.get(include=["metadatas", "documents"])
ids   = all_data["ids"]            or []
metas = all_data["metadatas"]      or []
docs  = all_data["documents"]      or []

print("=" * 70)
print(f"TOTAL CHUNKS IN CHROMADB: {len(ids)}")
print("=" * 70)

# Show chunk index: fund → sections
fund_sections = defaultdict(list)
for meta in metas:
    fund_sections[meta["scheme_name"]].append(meta["section"])

for fund, sections in fund_sections.items():
    print(f"\n{fund}")
    for s in sections:
        print(f"    - {s}")

# ── 2. Chunk length analysis ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CHUNK LENGTH ANALYSIS (characters)")
print("=" * 70)
lengths = [len(d) for d in docs]
print(f"  Min:  {min(lengths)}")
print(f"  Max:  {max(lengths)}")
print(f"  Avg:  {sum(lengths)//len(lengths)}")

# ── 3. Retrieval tests: cross-fund interference check ───────────────────────
test_queries = [
    ("What is the exit load of HDFC Mid Cap Fund?",           "HDFC Mid Cap Fund Direct Growth"),
    ("What is the minimum SIP for Parag Parikh?",             "Parag Parikh Long Term Value Fund Direct Growth"),
    ("Who manages the Motilal Oswal Midcap fund?",            "Motilal Oswal Focused Midcap 30 Fund Direct Growth"),
    ("What is the expense ratio of HDFC Silver ETF FOF?",     "HDFC Silver ETF FOF Direct Growth"),
    ("What are the 5 year returns of HDFC Equity Fund?",      "HDFC Equity Fund Direct Growth"),
    # Ambiguous - no fund named, should still find most relevant
    ("What is the exit load?",                                 None),
    ("What are the top holdings?",                             None),
]

print("\n" + "=" * 70)
print("RETRIEVAL TEST: top_k=3 results per query")
print("=" * 70)

for query, expected_fund in test_queries:
    print(f"\nQ: {query}")
    if expected_fund:
        print(f"   Expected fund: {expected_fund}")
    results = query_vector_db(query, top_k=3)
    for i, r in enumerate(results, 1):
        fund = r["metadata"]["scheme_name"]
        section = r["metadata"]["section"]
        dist = r["distance"]
        label = ""
        if expected_fund:
            label = " <-- CORRECT" if expected_fund in fund else " <-- WRONG FUND"
        print(f"   [{i}] dist={dist:.4f} | {fund[:35]:<35} | {section}{label}")
