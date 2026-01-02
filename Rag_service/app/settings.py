from pathlib import Path

# Project root: Prep/
BASE_DIR = Path(__file__).resolve().parents[2]

# Data paths
DATA_DIR = BASE_DIR / "Data"
PDF_DIR = DATA_DIR / "PDFiles"
VECTORSTORE_DIR = DATA_DIR / "Vectorstores"

# Vector DB config
COLLECTION_NAME = "semantic_chunks_v1"

# Chunking config
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Retrieval
TOP_K = 5