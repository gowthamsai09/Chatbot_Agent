from pathlib import Path
import os

# Project root: Prep/
BASE_DIR = Path(__file__).resolve().parents[2]

# Data paths
DATA_DIR = BASE_DIR / "Data"
PDF_DIR = DATA_DIR / "PDFiles"
VECTORSTORE_DIR = DATA_DIR / "Vectorstores"

# Vector DB config
# COLLECTION_NAME = "semantic_chunks_v1" # Local

# Qdrant Cloud
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "rag_documents"

# Hugging Face Inference
HF_TOKEN_POOL = [
    t.strip()
    for t in os.getenv("HF_TOKEN_POOL", "").split(",")
    if t.strip()
]
# HF_INFERENCE_API_KEY = os.getenv("HF_INFERENCE_API_KEY")
HF_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking config
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Retrieval
TOP_K = 5