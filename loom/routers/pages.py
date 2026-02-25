from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from loom.rendering import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")
