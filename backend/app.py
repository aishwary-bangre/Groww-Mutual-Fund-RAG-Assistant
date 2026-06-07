"""
app.py — FastAPI Backend Server
"""

import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend directory is in python path
sys.path.insert(0, "backend")

from engine import answer_query
from scheduler import start_scheduler, get_last_refresh_time
from config import HOST, PORT, GEMINI_LLM_MODEL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("backend.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager handles startup and shutdown logic.
    """
    logger.info("Starting up Groww Mutual Fund RAG Assistant backend...")
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
    
    yield
    
    logger.info("Shutting down Groww Mutual Fund RAG Assistant backend...")


app = FastAPI(
    title="Groww Mutual Fund RAG Assistant",
    description="RAG-powered conversational assistant for public mutual fund details.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Request/Response Models ──────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., description="The query string from the user.")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="The LLM-generated response or guardrail refusal message.")
    citation_url: str | None = Field(default=None, description="The URL of the source document used.")
    last_updated: str | None = Field(default=None, description="The scrape/refresh date of the source data.")
    intent: str = Field(..., description="The categorized intent: FACTUAL, ADVISORY, BLOCKED_PII, OUT_OF_SCOPE, or ERROR.")


# ── REST API Endpoints ─────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Accepts a user query, processes it through the RAG engine pipeline, and returns the result.
    """
    logger.info(f"Received query: {request.query}")
    try:
        result = answer_query(request.query)
        logger.info(f"Query processed successfully. Intent: {result.get('intent')}")
        return ChatResponse(
            answer=result.get("answer", ""),
            citation_url=result.get("citation_url"),
            last_updated=result.get("last_updated"),
            intent=result.get("intent", "ERROR")
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@app.get("/health")
def health_endpoint():
    """
    Returns API health status, the active LLM, the last database refresh date, and the ChromaDB record count.
    """
    db_count = 0
    db_status = "unreachable"
    try:
        import chromadb
        from config import VECTOR_STORE_DIR, CHROMA_COLLECTION
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_collection(CHROMA_COLLECTION)
        db_count = collection.count()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    return {
        "status": "healthy",
        "llm_model": GEMINI_LLM_MODEL,
        "database": {
            "status": db_status,
            "record_count": db_count,
        },
        "last_data_refresh": get_last_refresh_time()
    }


# ── Run Command (Development Server) ──────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Launching development server on {HOST}:{PORT}...")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
