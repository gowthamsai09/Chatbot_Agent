from langchain_chroma import Chroma
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from .settings import VECTORSTORE_DIR, COLLECTION_NAME

_embedding = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

_vectorstore = None


def get_embeddings():
    return _embedding


def get_vectorstore():
    global _vectorstore

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=str(VECTORSTORE_DIR),
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings()
        )

    return _vectorstore

get_vectorstore()
