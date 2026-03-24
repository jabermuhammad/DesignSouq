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

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}

_SUPABASE_CLIENT = None
_SUPABASE_CONFIG = (None, None)


def _get_supabase_client():
    global _SUPABASE_CLIENT, _SUPABASE_CONFIG
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not supabase_url or not supabase_key or create_client is None:
        return None
    if _SUPABASE_CLIENT is not None and _SUPABASE_CONFIG == (supabase_url, supabase_key):
        return _SUPABASE_CLIENT
    _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    _SUPABASE_CONFIG = (supabase_url, supabase_key)
    return _SUPABASE_CLIENT


def _validate_upload(upload: UploadFile) -> tuple[str, str]:
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    content_type = (upload.content_type or "").lower()

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    if content_type and not content_type.startswith("image/"):
        # Some browsers send application/octet-stream for images; trust extension if allowed.
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail="Invalid file type")

    return suffix, content_type or "application/octet-stream"


def save_upload_image(upload: UploadFile, folder: str = "uploads") -> str:
    suffix, content_type = _validate_upload(upload)
    client = _get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="Supabase storage is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )

    file_bytes = upload.file.read()
    object_name = f"{folder.rstrip('/')}/img_{uuid4().hex[:12]}{suffix}"

    supabase_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "").strip() or "design-haat"
    result = client.storage.from_(supabase_bucket).upload(
        object_name,
        file_bytes,
        {"content-type": content_type, "upsert": "true"},
    )

    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=500, detail="Image upload failed")

    public_url = client.storage.from_(supabase_bucket).get_public_url(object_name)
    if isinstance(public_url, dict):
        url_value = public_url.get("publicUrl") or public_url.get("public_url")
    else:
        url_value = str(public_url)

    if not url_value:
        raise HTTPException(status_code=500, detail="Unable to generate image URL")

    return url_value
