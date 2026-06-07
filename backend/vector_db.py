"""
vector_db.py — Chunking, Embedding & ChromaDB Vector Storage

Phase 3 pipeline:
  1. chunk_by_sections()   — Split fund documents into section-based chunks
  2. generate_embeddings() — Embed chunks via Gemini API          [Task 2]
  3. build_vector_store()  — Store in ChromaDB                    [Task 3]
  4. query_vector_db()     — Semantic retrieval                    [Task 4]
"""

import re
import sys
import json
from typing import Any
sys.path.insert(0, "backend")
from config import VECTOR_STORE_DIR

# Section header pattern used by parser.py
SECTION_PATTERN = re.compile(r"(?=\n=== )")


def chunk_by_sections(cleaned_text: str, scheme_metadata: dict) -> list[dict]:
    """
    Splits a structured fund document into section-based chunks.

    Strategy:
    - Split on '=== SECTION NAME ===' headers.
    - Each section becomes one independent, self-contained chunk.
    - The '=== FUND IDENTITY ===' block is prepended to every non-identity
      chunk so that each chunk knows which fund it belongs to, enabling
      precise retrieval even without metadata filters.

    Returns:
        List of chunk dicts: { text, section_name, metadata }
    """
    # Split the document at each section boundary
    raw_sections = SECTION_PATTERN.split(cleaned_text.strip())

    identity_block = ""
    chunks = []

    for raw in raw_sections:
        section = raw.strip()
        if not section:
            continue

        # Extract section name from the header line
        header_match = re.match(r"=== (.+?) ===", section)
        section_name = header_match.group(1).strip() if header_match else "GENERAL"

        if section_name == "FUND IDENTITY":
            identity_block = section
            # Include the identity block as its own chunk too
            chunks.append({
                "text": section,
                "section_name": section_name,
                "metadata": {
                    **scheme_metadata,
                    "section": section_name,
                }
            })
        else:
            # Prepend identity context to every other section
            chunk_text = f"{identity_block}\n\n{section}" if identity_block else section
            chunks.append({
                "text": chunk_text,
                "section_name": section_name,
                "metadata": {
                    **scheme_metadata,
                    "section": section_name,
                }
            })

    return chunks


def chunk_all_documents(documents: list[dict]) -> list[dict]:
    """
    Applies chunk_by_sections() to all documents returned by parser.load_all_documents().

    Returns a flat list of all chunks across all 5 funds.
    """
    all_chunks = []
    for doc in documents:
        fund_chunks = chunk_by_sections(
            cleaned_text=doc["cleaned_text"],
            scheme_metadata=doc["scheme_metadata"]
        )
        all_chunks.extend(fund_chunks)
        print(f"  {doc['scheme_metadata']['scheme_name']}: {len(fund_chunks)} chunks")
    return all_chunks


# ──────────────────────────────────────────────────────────────────────────────
# Placeholder stubs for Tasks 2, 3, 4 (implemented in subsequent phases)
# ──────────────────────────────────────────────────────────────────────────────

def generate_embeddings(chunks: list[dict]) -> list[dict]:
    """
    [Task 2] Embeds each chunk using Gemini text-embedding-004.

    - Uses task_type='retrieval_document' for indexing chunks.
    - Attaches the embedding vector to each chunk dict.
    - Returns the same list of chunks, now with an 'embedding' key added.
    """
    import time
    from google import genai
    from config import GEMINI_API_KEY, EMBEDDING_MODEL

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found. Set it in .env file.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"Generating embeddings for {len(chunks)} chunks via {EMBEDDING_MODEL}...")
    embedded_chunks = []

    for i, chunk in enumerate(chunks):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=chunk["text"],
                )
                if not result.embeddings:
                    raise RuntimeError(f"Gemini returned no embeddings for chunk {i}.")
                chunk["embedding"] = result.embeddings[0].values
                embedded_chunks.append(chunk)

                # Progress indicator
                if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
                    print(f"  Embedded {i + 1}/{len(chunks)} chunks...")

                # Base delay to stay within free-tier rate limits
                time.sleep(1.5)
                break  # Success — exit retry loop

            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)  # 10s, 20s backoff
                    print(f"  Rate limit hit on chunk {i}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  ERROR embedding chunk {i} ({chunk['section_name']} / "
                          f"{chunk['metadata'].get('scheme_name', '?')}): {e}")
                    break  # Give up after max retries


    print(f"Embedding complete. {len(embedded_chunks)}/{len(chunks)} chunks embedded.")
    return embedded_chunks


def build_vector_store(chunks: list[dict]) -> None:
    """
    [Task 3] Upserts all embedded chunks into a persistent ChromaDB collection.

    - Creates/opens a local ChromaDB instance at data/vector_store/.
    - Sanitizes metadata (ChromaDB only allows str, int, float, bool values).
    - Upserts chunks with: unique ID, embedding vector, document text, metadata.
    - Collection is persistent — survives restarts without re-embedding.
    """
    import chromadb
    from config import VECTOR_STORE_DIR, CHROMA_COLLECTION

    # Initialize persistent ChromaDB client
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    # Get or create the collection (idempotent)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}  # Use cosine similarity
    )

    ids, embeddings, documents, metadatas = [], [], [], []

    for i, chunk in enumerate(chunks):
        # Unique ID: fund slug + section + index
        fund_slug = chunk["metadata"].get("scheme_name", "fund").replace(" ", "_")[:30]
        chunk_id = f"{fund_slug}__{chunk['section_name']}__{i}"

        # Sanitize metadata: ChromaDB only allows str, int, float, bool
        clean_meta = {}
        for k, v in chunk["metadata"].items():
            if v is None:
                clean_meta[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean_meta[k] = v
            else:
                clean_meta[k] = str(v)

        ids.append(chunk_id)
        embeddings.append(chunk["embedding"])
        documents.append(chunk["text"])
        metadatas.append(clean_meta)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    print(f"Vector store built: {len(ids)} chunks upserted into ChromaDB.")
    print(f"Collection '{collection.name}' now has {collection.count()} documents.")
    print(f"Persisted at: {VECTOR_STORE_DIR}")


def query_vector_db(query_text: str, top_k: int = 3, fund_filter: str | None = None) -> list[dict]:
    """
    [Task 4] Embeds a user query and retrieves the top-K most relevant chunks.

    - Uses task_type='RETRIEVAL_QUERY' for query embedding (vs 'retrieval_document' for indexing).
    - Queries the persistent ChromaDB 'mutual_funds' collection.
    - If fund_filter is provided, restricts results to that fund via a where clause.
    - Returns list of { text, metadata, distance } dicts for the RAG engine.
    """
    import chromadb
    from google import genai
    from config import GEMINI_API_KEY, EMBEDDING_MODEL, VECTOR_STORE_DIR, CHROMA_COLLECTION

    # Embed the query
    client = genai.Client(api_key=GEMINI_API_KEY)
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query_text,
        config={"task_type": "RETRIEVAL_QUERY"}
    )
    if not result.embeddings:
        raise RuntimeError("Gemini returned no embeddings for the query.")
    query_embedding: list[float] = result.embeddings[0].values or []
    if not query_embedding:
        raise RuntimeError("Gemini returned empty embedding values for the query.")

    # Query ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_collection(CHROMA_COLLECTION)

    where_clause: dict[str, Any] | None = None
    if fund_filter is not None:
        where_clause = {"scheme_name": fund_filter}

    results = collection.query(
        query_embeddings=[query_embedding],  # type: ignore
        n_results=top_k,
        where=where_clause,
        include=["documents", "metadatas", "distances"]
    )

    # Null-safe defaults (ChromaDB types these as Optional)
    docs_list  = results["documents"]  or [[]]
    metas_list = results["metadatas"]  or [[]]
    dists_list = results["distances"]  or [[]]

    # Format output
    retrieved = []
    for doc, meta, dist in zip(docs_list[0], metas_list[0], dists_list[0]):
        retrieved.append({
            "text": doc,
            "metadata": meta,
            "distance": round(dist, 4)
        })

    return retrieved


# ──────────────────────────────────────────────────────────────────────────────
# Test: Run chunking on the cached cleaned_funds.json
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with open("data/cleaned_funds.json", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} fund documents.\n")
    print("Chunking by sections...")
    all_chunks = chunk_all_documents(documents)

    print(f"\nTotal chunks produced: {len(all_chunks)}")
    print("\n--- Sample Chunks ---")

    # Show the first 2 chunks from the first fund
    for chunk in all_chunks[:2]:
        print(f"\n[Section: {chunk['section_name']}]")
        print(f"[Fund: {chunk['metadata']['scheme_name']}]")
        print(chunk["text"][:400])
        print("...")
