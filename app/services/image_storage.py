from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app import config as _config  # ensure .env is loaded

try:
    from supabase import create_client
except Exception:  # pragma: no cover - optional dependency
    create_client = None

BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_IMAGE_DIR = BASE_DIR / "static" / "images"
LOCAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
)
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "").strip() or "design-haat"

_SUPABASE_CLIENT = None


def _get_supabase_client():
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT
    if not SUPABASE_URL or not SUPABASE_KEY or create_client is None:
        return None
    _SUPABASE_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _SUPABASE_CLIENT


def _validate_upload(upload: UploadFile) -> tuple[str, str]:
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    content_type = (upload.content_type or "").lower()

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    return suffix, content_type or "application/octet-stream"


def _save_local(upload: UploadFile, suffix: str) -> str:
    filename = f"img_{uuid4().hex[:12]}{suffix}"
    target = LOCAL_IMAGE_DIR / filename
    with target.open("wb") as out:
        out.write(upload.file.read())
    return filename


def save_upload_image(upload: UploadFile, folder: str = "uploads") -> str:
    suffix, content_type = _validate_upload(upload)
    client = _get_supabase_client()

    if client is None:
        return _save_local(upload, suffix)

    file_bytes = upload.file.read()
    object_name = f"{folder.rstrip('/')}/img_{uuid4().hex[:12]}{suffix}"

    result = client.storage.from_(SUPABASE_BUCKET).upload(
        object_name,
        file_bytes,
        {"content-type": content_type, "upsert": "true"},
    )

    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=500, detail="Image upload failed")

    public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(object_name)
    if isinstance(public_url, dict):
        url_value = public_url.get("publicUrl") or public_url.get("public_url")
    else:
        url_value = str(public_url)

    if not url_value:
        raise HTTPException(status_code=500, detail="Unable to generate image URL")

    return url_value
