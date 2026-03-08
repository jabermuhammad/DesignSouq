from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

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


def _table_exists(table: str) -> bool:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table}).first()
        return row is not None


def _ensure_column(table: str, column: str, ddl: str) -> None:
    if not _table_exists(table):
        return
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if column not in cols:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


# keep legacy databases compatible
_ensure_column("designers", "username", "username VARCHAR(80)")
_ensure_column("designers", "full_name", "full_name VARCHAR(120) NOT NULL DEFAULT ''")
_ensure_column("designers", "whatsapp", "whatsapp VARCHAR(40) NOT NULL DEFAULT ''")
_ensure_column("designers", "address", "address VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "bio", "bio TEXT NOT NULL DEFAULT ''")
_ensure_column("designers", "website_url", "website_url VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "facebook_url", "facebook_url VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "instagram_url", "instagram_url VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "behance_url", "behance_url VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "dribbble_url", "dribbble_url VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "password", "password VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "skills", "skills VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("designers", "profile_image", "profile_image VARCHAR(255) NOT NULL DEFAULT 'default-profile.svg'")
_ensure_column("designers", "cover_image", "cover_image VARCHAR(255) NOT NULL DEFAULT 'default-cover.svg'")

_ensure_column("viewers", "username", "username VARCHAR(80)")
_ensure_column("viewers", "full_name", "full_name VARCHAR(120) NOT NULL DEFAULT ''")
_ensure_column("viewers", "password", "password VARCHAR(255) NOT NULL DEFAULT ''")
_ensure_column("viewers", "profile_image", "profile_image VARCHAR(255) NOT NULL DEFAULT 'default-profile.svg'")

_ensure_column("projects", "description", "description TEXT NOT NULL DEFAULT ''")
_ensure_column("projects", "tags", "tags VARCHAR(255) NOT NULL DEFAULT ''")

app = FastAPI(title="Design Haat", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="design-haat-session-secret", same_site="lax", max_age=60 * 60 * 24 * 365 * 10)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(home.router)
app.include_router(designer.router)
app.include_router(viewer.router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
