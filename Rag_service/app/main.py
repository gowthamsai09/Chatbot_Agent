from fastapi import FastAPI
from app.api import router as api_router
from app.ui import router as ui_router

app = FastAPI(
    title="Knowledge Service",
    version="1.0.0"
)

app.include_router(ui_router)
app.include_router(api_router, prefix="/api")  # APIs at /api/*
