import re
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .settings import CHUNK_SIZE, CHUNK_OVERLAP
from .vector_store import get_vectorstore
import hashlib

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
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "book": book,
                        "author": author,
                        "chapter": chapter_title,
                        "domain": domain,
                        "source": pdf_path,
                        "content_hash": hash_value
                    }
                )
            )
    return documents

def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def content_hash(text: str) -> str:
    """
    Create a stable hash for deduplication.
    Prevents repeated paragraphs from poisoning retrieval.
    """

    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def ingest_pdf(
    pdf_path: str,
    book: str,
    author: str,
    domain: str
):
    """
    Full ingestion pipeline:
    PDF → chapters → chunks → dedup → vectorstore
    """

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

def retrieve(query: str, top_k: int = 5, domain: str = None):
    vectorstore = get_vectorstore()

    if domain:
        return vectorstore.similarity_search(
            query=query,
            k=top_k,
            filter={"domain": domain}
        )

    return vectorstore.similarity_search(
        query=query,
        k=top_k
    )