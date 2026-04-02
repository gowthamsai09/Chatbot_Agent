import os, logging, time
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
print("APP IMPORT STARTED")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Load env BEFORE importing app modules
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

# Create app immediately
app = FastAPI()

# Static files (CSS, JS, images) 
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Import routers AFTER app creation to avoid circular imports
from .api import router as api_router, eval_jobs, MAX_EVAL_TIME
from .ui import router as ui_router

# Register routers
app.include_router(ui_router)
app.include_router(api_router, prefix="/api")


# Simple health check - no dependencies
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ping")
def root():
    return {"message": "RAG Service Running"}


# Background cleanup for eval jobs 
def cleanup_jobs():
    while True:
        time.sleep(300)  # every 5 minutes
        now = time.time()
        for job_id in list(eval_jobs.keys()):
            try:
                job = eval_jobs[job_id]
                if job["status"] != "running":
                    eval_jobs.pop(job_id, None)
                elif now - job["start_time"] > MAX_EVAL_TIME:
                    job["status"] = "timeout"
            except Exception:
                pass


@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "8000")
    logging.info(f"Server started on port {port}")
    import threading
    threading.Thread(target=cleanup_jobs, daemon=True).start()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )