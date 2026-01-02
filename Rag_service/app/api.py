from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from .rag_engine import ingest_pdf, retrieve
from .ingestion_service import ingest_all_pdfs, get_knowledge_summary
from .settings import TOP_K
from .agent_service import run_agent

router = APIRouter()


# Request / Response Models

class IngestRequest(BaseModel):
    pdf_path: str
    book: str
    author: str
    domain: str


class QueryRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    top_k: Optional[int] = TOP_K


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    coverage: Optional[str] = None
    path_taken: Optional[str] = None

# API Endpoints
@router.post("/ingest")
def ingest(request: IngestRequest):
    """
    Ingest a single PDF into the vector store.
    Safe to call multiple times (dedup enabled).
    """
    try:
        return ingest_pdf(
            pdf_path=request.pdf_path,
            book=request.book,
            author=request.author,
            domain=request.domain
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/all")
def ingest_all():
    """
    Automatically ingest all PDFs present in the PDF directory.
    Skips already indexed PDFs.
    """
    try:
        return ingest_all_pdfs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """
    Query the RAG system with optional domain-aware retrieval.
    """
    try:
        results = retrieve(
            query=request.query,
            top_k=request.top_k,
            domain=request.domain
        )

        if not results:
            return QueryResponse(
                answer="I do not have enough information to answer this question.",
                sources=[]
            )

        # Collect unique sources
        sources = list({
            doc.metadata.get("source", "unknown")
            for doc in results
        })

        agent_result = run_agent(request.query)
        answer = agent_result["answer"]
        coverage = agent_result.get("coverage")
        path_taken = agent_result.get("path_taken")
        return QueryResponse(
            answer=answer,
            sources=sources,
            coverage=coverage,
            path_taken=path_taken
        )

    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge")
def knowledge():
    """
    Returns what data the system is trained on:
    books, domains, and sample chapters.
    Used by UI for transparency.
    """
    try:
        return get_knowledge_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health():
    """
    Health check endpoint.
    """
    return {"status": "ok"}