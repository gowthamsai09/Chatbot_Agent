from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File

from .rag_engine import ingest_pdf
from .ingestion_service import get_knowledge_summary
from .settings import TOP_K
from .rag_engine import answer_query
from .ingestion_service import ingest_uploaded_document,ingest_url

router = APIRouter()


# Request / Response Models
class IngestRequest(BaseModel):
    pdf_path: str
    book: str
    author: str
    domain: str


class QueryRequest(BaseModel):
    query: str
    session_id: str
    # hf_token: str
    domain: Optional[str] = None
    document_id: Optional[str] = None
    top_k: Optional[int] = TOP_K


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    coverage: Optional[str] = None
    path_taken: Optional[str] = None

class UrlUploadRequest(BaseModel):
    url: str
    domain: str = "general"

# API Endpoints

# Ingest a single PDF into the vector store.
@router.post("/ingest")
def ingest(request: IngestRequest):
    try:
        return ingest_pdf(
            pdf_path=request.pdf_path,
            book=request.book,
            author=request.author,
            domain=request.domain
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Automatically ingest all PDFs present in the PDF directory. Skips already indexed PDFs
# @router.post("/ingest/all") # No longer required
# def ingest_all():
#     try:
#         return ingest_all_pdfs()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# Query the RAG system with optional domain-aware retrieval.
@router.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    try:
        result = answer_query(
            query=request.query,
            # hf_token=request.hf_token,
            domain=request.domain,
            document_id=request.document_id,
            top_k=request.top_k,
        )

        return QueryResponse(
            answer=result["answer"],
            sources=[
                f'{src.get("document")} - {src.get("chapter")}'
                for src in result.get("sources", [])
            ],
            coverage="vectorstore",
            path_taken="retrieval → hf_llm"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Returns what data the system is trained on
@router.get("/knowledge")
def knowledge():
    try:
        return get_knowledge_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    domain: str = "general"
):

    try:
        result = ingest_uploaded_document(
            upload_file=file,
            domain=domain
        )
        return {
            "status": result.get("status"),
            "document": result.get("document"),
            "document_id": result.get("document_id"),
            "chunks_added": result.get("details", {}).get("chunks_added", 0)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.post("/upload/url")
def upload_url(request: UrlUploadRequest):

    result = ingest_url(
        url=request.url,
        domain=request.domain
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result

@router.get("/health")
def health():
    return {"status": "ok"}