from fastapi import FastAPI
import logging
import os
from app.api import router as api_router
from app.ui import router as ui_router
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    port = os.getenv("PORT", "8000")
    print(f"FastAPI app started successfully on port {port}")
    print(f"Environment: {'Render' if os.getenv('RENDER') else 'Local'}")

app.include_router(ui_router)
app.include_router(api_router, prefix="/api")


# Health check endpoint for Render
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RAG Knowledge Assistant"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
