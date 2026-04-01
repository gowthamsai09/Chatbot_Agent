import os
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from fastapi import FastAPI
import logging

# Load env BEFORE importing app modules
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

# Create app immediately
app = FastAPI()

# Import routers AFTER app creation to avoid circular imports
from app.api import router as api_router
from app.ui import router as ui_router

# Register routers
app.include_router(ui_router)
app.include_router(api_router, prefix="/api")

# Simple health check - no dependencies
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "RAG Service Running"}

# Startup logging
@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "8000")
    logging.info(f"Server started on port {port}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )