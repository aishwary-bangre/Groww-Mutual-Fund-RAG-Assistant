"""
scheduler.py — Daily Data Refresh Scheduler
"""

import sys
import time
import datetime
import threading
import logging
import hashlib
import json
from pathlib import Path

# Ensure backend directory is in the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import parser
import vector_db
from config import REFRESH_TIME, VECTOR_STORE_DIR, CHROMA_COLLECTION, DATA_DIR

logger = logging.getLogger("backend.scheduler")

# Cache tracking the last successful refresh completion time
_LAST_RUN_TIME = None


def get_text_hash(text: str) -> str:
    """Computes SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_daily_refresh():
    """
    Main workflow for the daily database refresh:
    1. Scrapes latest mutual fund data from Groww website.
    2. Overwrites local JSON cache with clean document data.
    3. Breaks pages down into sections.
    4. Compares SHA-256 hashes against database records to reuse embeddings.
    5. Requests embeddings from Gemini only for modified/new text.
    6. Performs an idempotent upsert to ChromaDB.
    """
    global _LAST_RUN_TIME
    logger.info("Triggering scheduled daily data refresh...")
    
    try:
        # 1. Scrape latest data from Groww
        documents = parser.load_all_documents()
        if not documents:
            logger.error("Scraper returned no documents. Aborting daily refresh.")
            return

        # Update cache file
        cache_path = DATA_DIR / "cleaned_funds.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(documents, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully cached clean fund data to {cache_path}")
        except Exception as e:
            logger.warning(f"Could not save JSON cache file: {e}")

        # 2. Chunk fresh documents by sections
        chunks = vector_db.chunk_all_documents(documents)
        logger.info(f"Generated {len(chunks)} chunks from fresh scrap.")

        # 3. Retrieve existing embeddings from ChromaDB for hash comparison
        import chromadb
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        
        existing_embeddings = {}
        existing_hashes = {}
        
        try:
            collection = chroma_client.get_collection(name=CHROMA_COLLECTION)
            existing = collection.get(include=["documents", "embeddings"])
            
            if existing and existing.get("ids"):
                docs = existing.get("documents") or []
                embs = existing.get("embeddings") or []
                for idx, cid in enumerate(existing["ids"]):
                    if idx < len(docs) and idx < len(embs):
                        doc_text = docs[idx]
                        emb = embs[idx]
                        
                        if doc_text is not None and emb is not None:
                            existing_hashes[cid] = get_text_hash(doc_text)
                            existing_embeddings[cid] = emb.tolist() if hasattr(emb, "tolist") else list(emb)
                        
                logger.info(f"Loaded {len(existing_hashes)} existing records from ChromaDB for hash checks.")
        except Exception as e:
            logger.warning(f"No existing records loaded from ChromaDB (collection might be empty): {e}")

        # 4. Filter unchanged chunks to save API costs
        chunks_to_embed = []
        
        for i, chunk in enumerate(chunks):
            # Formulate ID matching vector_db.build_vector_store
            fund_slug = chunk["metadata"].get("scheme_name", "fund").replace(" ", "_")[:30]
            chunk_id = f"{fund_slug}__{chunk['section_name']}__{i}"
            
            chunk_hash = get_text_hash(chunk["text"])
            
            if chunk_id in existing_hashes and existing_hashes[chunk_id] == chunk_hash:
                # Text hasn't changed, reuse existing embedding vector
                chunk["embedding"] = existing_embeddings[chunk_id]
            else:
                # New or modified text, requires new API call to embed
                chunks_to_embed.append(chunk)

        logger.info(
            f"Hash comparison results: {len(chunks) - len(chunks_to_embed)} chunks unchanged (reused). "
            f"{len(chunks_to_embed)} chunks changed or new (need embedding)."
        )

        # 5. Embed only the modified chunks
        if chunks_to_embed:
            # generate_embeddings mutates dictionaries in chunks_to_embed, which automatically
            # updates the same dictionary references inside the 'chunks' list
            vector_db.generate_embeddings(chunks_to_embed)
            logger.info(f"Successfully generated new embeddings for {len(chunks_to_embed)} chunks.")

        # 6. Store and persist inside ChromaDB
        # Using the original 'chunks' list preserves the exact index ordering of IDs
        vector_db.build_vector_store(chunks)
        logger.info("Database upsert successful. Daily refresh completed.")
            
        _LAST_RUN_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Daily refresh cycle finished successfully at {_LAST_RUN_TIME}")
        
    except Exception as e:
        logger.error(f"Daily refresh cycle failed: {e}", exc_info=True)


def scheduler_loop(refresh_time_str: str):
    """
    Infinite background loop sleeping until the daily target REFRESH_TIME.
    """
    logger.info(f"Starting scheduler loop target time: {refresh_time_str}")
    
    # Parse HH:MM format
    try:
        target_hour, target_min = map(int, refresh_time_str.split(':'))
    except Exception as e:
        logger.error(f"Invalid REFRESH_TIME format '{refresh_time_str}', defaulting to 00:00. Error: {e}")
        target_hour, target_min = 0, 0

    # Initial Staleness Check: Run immediately if data is old, missing, or database is empty
    try:
        import chromadb
        db_count = 0
        try:
            chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
            collection = chroma_client.get_collection(CHROMA_COLLECTION)
            db_count = collection.count()
        except Exception:
            db_count = 0

        cache_path = DATA_DIR / "cleaned_funds.json"
        if db_count == 0:
            logger.info("ChromaDB collection is empty or missing. Running initial catch-up refresh.")
            run_daily_refresh()
        elif cache_path.exists():
            import time as _time
            mtime = cache_path.stat().st_mtime
            age_hours = (_time.time() - mtime) / 3600
            if age_hours > 24:
                logger.info(f"Database cache is {age_hours:.1f} hours old. Running immediate catch-up refresh.")
                run_daily_refresh()
        else:
            logger.info("No existing database found. Running initial catch-up refresh.")
            run_daily_refresh()
    except Exception as e:
        logger.error(f"Error during initial staleness check: {e}")

    while True:
        try:
            now = datetime.datetime.now()
            target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
            
            if target_time <= now:
                # Target time already passed today, schedule for tomorrow
                target_time += datetime.timedelta(days=1)
                
            sleep_seconds = (target_time - now).total_seconds()
            logger.info(f"Next database refresh cycle scheduled at {target_time} (sleeping for {sleep_seconds:.1f}s)")
            
            time.sleep(sleep_seconds)
            
            # Fire refresh
            run_daily_refresh()
            
        except Exception as e:
            logger.error(f"Error in scheduler execution loop: {e}")
            time.sleep(60)  # Wait 60s before restarting cycle in case of clock errors


def start_scheduler():
    """
    Launches the daily refresh scheduler loop in a background daemon thread.
    """
    thread = threading.Thread(
        target=scheduler_loop,
        args=(REFRESH_TIME,),
        daemon=True,
        name="GrowwRefreshScheduler"
    )
    thread.start()
    logger.info("Daily refresh scheduler background thread started successfully.")


def get_last_refresh_time() -> str | None:
    """
    Gets the timestamp string of the last successful refresh run.
    """
    global _LAST_RUN_TIME
    return _LAST_RUN_TIME
