# Ad-Ops-Autopilot — FastAPI application
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import auth, campaigns, competitive, curation, dashboard, progress, sessions, share
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Ad-Ops-Autopilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://nerdy-three.vercel.app",
        "https://*.vercel.app",
        "https://nerdy-production-290d.up.railway.app",
        "https://*.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check for load balancers and Docker."""
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(progress.router, prefix="/api/sessions", tags=["progress"])
app.include_router(dashboard.router, prefix="/api/sessions", tags=["dashboard"])
app.include_router(curation.router, prefix="/api/sessions", tags=["curation"])
app.include_router(share.router, prefix="/api/sessions", tags=["share"])
app.include_router(share.shared_router, prefix="/api/shared", tags=["shared"])
app.include_router(dashboard.competitive_router, prefix="/api/competitive", tags=["competitive"])
app.include_router(competitive.router)
app.include_router(dashboard.global_dashboard_router, prefix="/api/dashboard", tags=["global-dashboard"])

# Media serving — public reads (browsers can't attach Authorization to <img> tags).
# Path-traversal guarded; URLs are non-enumerable hashed ad IDs.
_images_dir = Path("output/images")
_images_dir.mkdir(parents=True, exist_ok=True)
_videos_dir = Path("output/videos")
_videos_dir.mkdir(parents=True, exist_ok=True)


@app.get("/api/images/{filename:path}")
def serve_image(filename: str):
    """Serve generated images.

    Public route: browser <img src> tags cannot attach an Authorization header,
    so requiring a Bearer token here breaks rendering. URLs contain hashed ad
    IDs (not enumerable), and the metadata endpoints that expose these URLs
    are still auth-gated.
    """
    safe_path = _images_dir / filename
    if ".." in filename or not safe_path.resolve().is_relative_to(_images_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(safe_path)


@app.get("/api/videos/{filename:path}")
def serve_video(filename: str):
    """Serve generated videos. See serve_image for why this is public."""
    safe_path = _videos_dir / filename
    if ".." in filename or not safe_path.resolve().is_relative_to(_videos_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(safe_path)
