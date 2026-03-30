from fastapi import FastAPI
import logging
from app.api import router as api_router
from app.ui import router as ui_router
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    print("FastAPI app started successfully")

app.include_router(ui_router)
app.include_router(api_router, prefix="/api")