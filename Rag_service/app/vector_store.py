from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from .settings import VECTORSTORE_DIR, COLLECTION_NAME

_embedding = None
_vectorstore = None


def get_embeddings():
    global _embedding
    if _embedding is None:
        _embedding = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
    return _embedding


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=str(VECTORSTORE_DIR),
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings()
        )
    return _vectorstore
