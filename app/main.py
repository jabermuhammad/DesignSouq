import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config as _config  # ensure .env is loaded
from app.admin import router as admin_router
from app.database import Base, engine
from app.routers import designer, home, viewer

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

for path in [
    STATIC_DIR,
    STATIC_DIR / "css",
    STATIC_DIR / "js",
    STATIC_DIR / "images",
]:
    path.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Design Haat", version="1.0.0")
session_secret = os.getenv("SESSION_SECRET", "design-haat-session-secret")
session_https_only = os.getenv("SESSION_HTTPS_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    max_age=60 * 60 * 24 * 365 * 10,
    https_only=session_https_only,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(home.router)
app.include_router(designer.router)
app.include_router(viewer.router)
app.include_router(admin_router)


@app.get("/health")
def health_check():
    return {"status": "online", "message": "DesignSouq is awake!"}


@app.get("/ping")
def ping():
    return {"status": "ok"}
