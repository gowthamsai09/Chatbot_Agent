print("STEP 2: api.py loaded")
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File

router = APIRouter()


# Request / Response Models
class TokenRequest(BaseModel):
    hf_token: str


@router.post("/set-token")
def set_token(request: TokenRequest):
    try:
        from .settings import set_hf_token
        
        # Empty token = use ENV pool
        token_to_set = request.hf_token.strip() if request.hf_token else ""
        
        set_hf_token(token_to_set)
        
        if token_to_set:
            message = "User token stored successfully"
        else:
            message = "Configured to use server token pool"

        return {
            "status": "success", 
            "message": message
        }
    
    except Exception as e:
        import traceback
        print(f"Error in set-token: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }
    
class IngestRequest(BaseModel):
    pdf_path: str
    book: str
    author: str
    domain: str


class QueryRequest(BaseModel):
    from .settings import TOP_K, get_hf_token,set_hf_token,HF_TOKEN_POOL
    query: str
    session_id: str
    hf_token: Optional[str] = None
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

# For evaluation metrics using ragas
class EvalRequest(BaseModel):
    test_questions: List[str]
    session_id: str
    hf_token: str

# API Endpoints
# Ingest a single PDF into the vector store.
@router.post("/ingest")
def ingest(request: IngestRequest):
    from .rag_engine import ingest_pdf
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
    from .rag_engine import answer_query
    # hf_token = request.hf_token or get_hf_token()
    try:
        result = answer_query(
            query=request.query,
            # hf_token=hf_token,
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
    from .ingestion_service import get_knowledge_summary
    try:
        return get_knowledge_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
def upload_document(file: UploadFile = File(...),domain: str = "general"):
    from .ingestion_service import ingest_uploaded_document
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
    from .ingestion_service import ingest_url
    result = ingest_url(
        url=request.url,
        domain=request.domain
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result

# Eval endpoint, runs Ragas on live pipeline
@router.post("/eval")
def eval_rag(request: EvalRequest):
    from .settings import get_hf_token,set_hf_token,HF_TOKEN_POOL
    from .eval_service import run_eval
    try:
        # hf_token = request.hf_token or get_hf_token()
        # Store token if user provided
        # if request.hf_token:
        set_hf_token(request.hf_token)

        # Validate token exists (user OR ENV)
        user_token = get_hf_token()
        if not user_token and not HF_TOKEN_POOL:
            raise HTTPException(
                status_code=400,
                detail="No HuggingFace token provided (UI or ENV)"
            )

        scores = run_eval(
            test_questions=request.test_questions,
            session_id=request.session_id,
            # hf_token=token
        )
        return scores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
def health():
    return {"status": "ok"}