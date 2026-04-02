from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent / "static"


@router.get("/", response_class=FileResponse)
def ui():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")