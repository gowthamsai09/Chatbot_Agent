from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from .settings import (
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    HF_INFERENCE_API_KEY,
    HF_EMBEDDING_MODEL
)

_vectorstore = None
_embeddings = None


def get_embeddings():
    global _embeddings

    if _embeddings is None:
        _embeddings = HuggingFaceEndpointEmbeddings(
        huggingfacehub_api_token=HF_INFERENCE_API_KEY,
        model=HF_EMBEDDING_MODEL
    )


    return _embeddings


def get_vectorstore():
    global _vectorstore

    if _vectorstore is None:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )

        _vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=get_embeddings()
        )

    return _vectorstore