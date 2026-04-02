import os,logging,time
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
print("APP IMPORT STARTED")
from fastapi import FastAPI

# Load env BEFORE importing app modules
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

# Create app immediately
app = FastAPI()

# Import routers AFTER app creation to avoid circular imports
from .api import router as api_router,eval_jobs,MAX_EVAL_TIME
from .ui import router as ui_router

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
# @app.on_event("startup")
# async def startup_event():
#     port = os.getenv("PORT", "8000")
#     logging.info(f"Server started on port {port}")

def cleanup_jobs():
    while True:
        time.sleep(300)  # every 5 minutes

        now = time.time()

        for job_id in list(eval_jobs.keys()):
            try:
                job = eval_jobs[job_id]

                # Remove completed/failed jobs
                if job["status"] != "running":
                    eval_jobs.pop(job_id, None)

                # Mark timeout (do not delete immediately)
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