import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from backend.routes.scouting import router
from backend.database import init_db
from backend.config import HIGHLIGHTS_DIR, UPLOADS_DIR
import logging
from contextlib import asynccontextmanager

DIST_DIR = Path(__file__).parent.parent / "frontend-dist"

os.makedirs(HIGHLIGHTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Storage ready: highlights={HIGHLIGHTS_DIR} uploads={UPLOADS_DIR}")
    init_db()
    yield


app = FastAPI(title="Pathfinder -- Esports Talent Scout", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    required_key = os.environ.get("PATHFINDER_API_KEY")
    if required_key and request.url.path.startswith("/api/"):
        if request.headers.get("x-api-key") != required_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


app.include_router(router, prefix="/api")
app.mount("/highlights", StaticFiles(directory=HIGHLIGHTS_DIR), name="highlights")

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(DIST_DIR / "favicon.svg")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(DIST_DIR / "index.html")
