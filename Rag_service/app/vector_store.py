from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import random

from .settings import (
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    HF_TOKEN_POOL,
    HF_EMBEDDING_MODEL,
    get_hf_token
)

_vectorstore = None
_embeddings = None
_qdrant_client = None



def _get_hf_token() -> str:
    """
    Pick a token safely:
    1. Use user-provided token if available
    2. Otherwise use token pool
    3. If nothing available → return None (do NOT crash app)
    """

    user_token = get_hf_token()

    # Priority 1: user token
    if user_token:
        return user_token

    # Priority 2: token pool
    if HF_TOKEN_POOL:
        return random.choice(HF_TOKEN_POOL)

    # Final fallback → DO NOT crash app
    print("HF token missing (user + ENV). Features will not work.")
    return None


# def get_embeddings():
#     global _embeddings

#     if _embeddings is None:
#         _embeddings = HuggingFaceEndpointEmbeddings(
#             huggingfacehub_api_token=_get_hf_token(),
#             model=HF_EMBEDDING_MODEL
#         )

#     return _embeddings

# Load only when needed.
def get_embeddings():
    global _embeddings

    if _embeddings is None:
        token = _get_hf_token()

        if not token:
            print("Cannot initialize embeddings: No HF token")
            return None

        try:
            print("Initializing embeddings...")
            _embeddings = HuggingFaceEndpointEmbeddings(
                huggingfacehub_api_token=token,
                model=HF_EMBEDDING_MODEL
            )
        except Exception as e:
            print("Embedding init failed:", str(e))
            return None

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

        # _vectorstore = QdrantVectorStore(
        #     client=client,
        #     collection_name=COLLECTION_NAME,
        #     embedding=get_embeddings()
        # )

        embeddings = get_embeddings()
        if embeddings is None:
            print("Embeddings not available, skipping vectorstore init")
            return None

        _vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings
        )
    return _vectorstore
