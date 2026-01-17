import re
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .settings import CHUNK_SIZE, CHUNK_OVERLAP
from .vector_store import get_vectorstore
from qdrant_client.models import Filter, FieldCondition, MatchValue
from .ingestion_service import generate_document_id
import hashlib
from .llm_service import generate_answer

CHAPTER_REGEX = re.compile(
    r"(chapter\s+\d+[:.\s]+.*)|(^\d+\s+.*)",
    re.IGNORECASE | re.MULTILINE
)


def extract_chapters(pdf_path: str):
    reader = PdfReader(pdf_path)

    chapters = []
    current_title = "Introduction"
    buffer = []

    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue

        matches = CHAPTER_REGEX.findall(text)
        if matches:
            # Save previous chapter
            if buffer:
                chapters.append((current_title, "\n".join(buffer)))
                buffer = []

            # Pick first detected title
            current_title = matches[0][0].strip()

        buffer.append(text)

    if buffer:
        chapters.append((current_title, "\n".join(buffer)))

    return chapters

def build_documents_from_pdf(
    pdf_path: str,
    book: str,
    author: str,
    domain: str
):
    chapters = extract_chapters(pdf_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    documents = []

    for chapter_title, chapter_text in chapters:
        cleaned_text = clean_text(chapter_text)
        chunks = splitter.split_text(cleaned_text)
        for chunk in chunks:
            hash_value = content_hash(chunk)
            doc_id = generate_document_id(book)
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "document_id": doc_id,
                        "document_name": book,
                        "book": book,
                        "author": author,
                        "chapter": chapter_title,
                        "domain": domain,
                        "source": "upload",
                        "chunk_id": hash_value,
                        "content_hash": hash_value
                    }
                )
            )
    return documents

def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

#  Create a stable hash for deduplication. Prevents repeated paragraphs from poisoning retrieval.
def content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

#  Full ingestion pipeline:PDF → chapters → chunks → dedup → vectorstore
def ingest_pdf(
    pdf_path: str,
    book: str,
    author: str,
    domain: str
    ):
    vectorstore = get_vectorstore()

    documents = build_documents_from_pdf(
        pdf_path=pdf_path,
        book=book,
        author=author,
        domain=domain
    )

    if not documents:
        return {"status": "no_content"}

    # OPTIONAL: Deduplication using content_hash
    existing_hashes = set()

    try:
        existing_docs = vectorstore.get(include=["metadatas"])
        for meta in existing_docs.get("metadatas", []):
            if meta and "content_hash" in meta:
                existing_hashes.add(meta["content_hash"])
    except Exception:
        pass

    new_docs = [
        doc for doc in documents
        if doc.metadata["content_hash"] not in existing_hashes
    ]

    if not new_docs:
        return {"status": "already_ingested"}

    vectorstore.add_documents(new_docs)

    return {
        "status": "ingested",
        "chunks_added": len(new_docs)
    }

def retrieve(query: str, top_k: int = 5, domain: str = None, document_id: str = None):
    vectorstore = get_vectorstore()
    conditions = []

    if domain:
        conditions.append(
            FieldCondition(
                key="metadata.domain",
                match=MatchValue(value=domain)
            )
        )

    if document_id:
        conditions.append(
            FieldCondition(
                key="metadata.document_id",
                match=MatchValue(value=document_id)
            )
        )

    search_filter = Filter(must=conditions) if conditions else None

    return vectorstore.similarity_search(
        query=query,
        k=top_k,
        filter=search_filter
    )

def answer_query(
    query: str,
    hf_token: str,
    domain: str = None,
    document_id: str = None,
    top_k: int = 5,
):
    # Step 1: retrieve relevant chunks
    docs = retrieve(
        query=query,
        top_k=top_k,
        domain=domain,
        document_id=document_id,
    )

    if not docs:
        return {
            "answer": "I do not have enough information.",
            "sources": []
        }

    # Step 2: build context
    context = "\n\n".join(doc.page_content for doc in docs)

    # Step 3: call LLM
    answer = generate_answer(
        question=query,
        context=context,
        hf_token=hf_token
    )

    # Step 4: return structured response
    return {
        "answer": answer,
        "sources": [
            {
                "document": doc.metadata.get("document_name"),
                "chapter": doc.metadata.get("chapter"),
            }
            for doc in docs
        ]
    }