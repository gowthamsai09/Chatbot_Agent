from fastapi import FastAPI
from .api import router as api_router
from .ui import router as ui_router

app = FastAPI(
    title="Knowledge Service",
    version="1.0.0"
)

app.include_router(ui_router)
app.include_router(api_router, prefix="/api")  # APIs at /api/*
