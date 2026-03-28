from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import random

def _get_hf_token() -> str:
    if not HF_TOKEN_POOL:
        raise RuntimeError(
            "HF_TOKEN_POOL is empty. Set HF_TOKEN_POOL env var in Render."
        )
    return random.choice(HF_TOKEN_POOL)


from .settings import (
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    HF_TOKEN_POOL,
    HF_EMBEDDING_MODEL
)

_vectorstore = None
_embeddings = None
_qdrant_client = None


def get_embeddings():
    global _embeddings

    if _embeddings is None:
        _embeddings = HuggingFaceEndpointEmbeddings(
            huggingfacehub_api_token=_get_hf_token(),
            model=HF_EMBEDDING_MODEL
        )

    return _embeddings


def get_qdrant_client():
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30
        )

    return _qdrant_client


def _ensure_payload_indexes(client: QdrantClient):
    """ Ensures required payload indexes exist."""

    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="metadata.document_id",
            field_schema=PayloadSchemaType.KEYWORD
        )
    except Exception:
        pass  

    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="metadata.domain",
            field_schema=PayloadSchemaType.KEYWORD
        )
    except Exception:
        pass


def get_vectorstore():
    global _vectorstore

    if _vectorstore is None:
        client = get_qdrant_client()
        
        _ensure_payload_indexes(client)

        _vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=get_embeddings()
        )

    return _vectorstore