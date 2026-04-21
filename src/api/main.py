"""
LLM Dixit Arena — FastAPI application entry point.

Run with:
    cd LLM_dixit
    uvicorn src.api.main:app --reload --port 8000

Or from the src/ directory:
    PYTHONPATH=src uvicorn api.main:app --reload --port 8000
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure src/ is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.routes.collections import router as collections_router
from api.routes.games import router as games_router
from api.routes.leaderboard import router as leaderboard_router
from api.routes.ws import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="LLM Dixit Arena",
    description="Run and watch LLM models compete at Dixit",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(collections_router)
app.include_router(games_router)
app.include_router(leaderboard_router)
app.include_router(ws_router)

# Serve card images from data/ directory
DATA_DIR = os.getenv("DATA_DIR", "data")


@app.get("/api/images/{path:path}")
async def serve_image(path: str):
    full_path = os.path.join(DATA_DIR, path)
    if not os.path.isfile(full_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(full_path)


# Serve React frontend (built output)
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for client-side routing."""
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
