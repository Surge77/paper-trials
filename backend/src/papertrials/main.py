import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from papertrials.api import router
from papertrials.config import get_settings

# The built frontend, if present, is served from the same port so a phone on
# the same Wi-Fi only needs one address.
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app() -> FastAPI:
    app = FastAPI(title="Paper Trials", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            try:
                candidate = (FRONTEND_DIST / path).resolve()
            except (OSError, ValueError):  # e.g. a null byte in the path
                candidate = FRONTEND_DIST / "index.html"
            if path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    uvicorn.run("papertrials.main:app", host=settings.host, port=settings.port)
