from pathlib import Path
from typing import List, Dict, Set

from .settings import PDF_DIR
from .rag_engine import ingest_pdf
from .vector_store import get_vectorstore

def get_indexed_pdf_sources() -> Set[str]:
    """
    Reads vector store metadata and returns
    a set of PDF paths already indexed.
    """
    vectorstore = get_vectorstore()
    indexed_sources = set()

    try:
        data = vectorstore.get(include=["metadatas"])
        for meta in data.get("metadatas", []):
            if meta and "source" in meta:
                indexed_sources.add(meta["source"])
    except Exception:
        pass

    return indexed_sources

def ingest_all_pdfs(
    default_author: str = "Unknown",
    default_domain: str = "general"
) -> Dict[str, int]:
    """
    Scans PDF_DIR and ingests only new PDFs.
    """

    indexed_sources = get_indexed_pdf_sources()

    total_found = 0
    newly_ingested = 0
    skipped = 0

    for pdf_path in Path(PDF_DIR).glob("*.pdf"):
        total_found += 1

        pdf_str = str(pdf_path)

        if pdf_str in indexed_sources:
            skipped += 1
            continue

        # Use filename as book name (can improve later)
        book_name = pdf_path.stem

        result = ingest_pdf(
            pdf_path=pdf_str,
            book=book_name,
            author=default_author,
            domain=default_domain
        )

        if result.get("status") == "ingested":
            newly_ingested += 1

    return {
        "pdfs_found": total_found,
        "pdfs_ingested": newly_ingested,
        "pdfs_skipped": skipped
    }

def get_knowledge_summary() -> Dict[str, List[str]]:
    """
    Returns high-level visibility into indexed data:
    books, domains, chapters.
    """
    vectorstore = get_vectorstore()

    books = set()
    domains = set()
    chapters = set()

    try:
        data = vectorstore.get(include=["metadatas"])
        for meta in data.get("metadatas", []):
            if not meta:
                continue

            books.add(meta.get("book", "unknown"))
            domains.add(meta.get("domain", "unknown"))
            chapters.add(meta.get("chapter", "unknown"))
    except Exception:
        pass

    return {
        "books": sorted(books),
        "domains": sorted(domains),
        "sample_chapters": sorted(list(chapters))[:10]
    }
