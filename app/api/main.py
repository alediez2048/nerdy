# Ad-Ops-Autopilot — FastAPI application
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
        "http://127.0.0.1:5173",
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


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(progress.router, prefix="/sessions", tags=["progress"])
app.include_router(dashboard.router, prefix="/sessions", tags=["dashboard"])
app.include_router(curation.router, prefix="/sessions", tags=["curation"])
app.include_router(share.router, prefix="/sessions", tags=["share"])
app.include_router(share.shared_router, prefix="/shared", tags=["shared"])
app.include_router(dashboard.competitive_router, prefix="/competitive", tags=["competitive"])
app.include_router(competitive.router)
app.include_router(dashboard.global_dashboard_router, prefix="/dashboard", tags=["global-dashboard"])

# Serve generated images as static files
_images_dir = Path("output/images")
_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")

# Serve generated videos as static files (PC-03)
_videos_dir = Path("output/videos")
_videos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(_videos_dir)), name="videos")
