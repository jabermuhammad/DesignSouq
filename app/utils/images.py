from __future__ import annotations

from typing import Optional


def resolve_image_url(value: str | None, default: str | None = None) -> str:
    clean = (value or "").strip()
    if clean:
        if clean.startswith("http://") or clean.startswith("https://") or clean.startswith("/static/"):
            return clean
        return f"/static/images/{clean}"

    if not default:
        return ""

    clean_default = default.strip()
    if clean_default.startswith("http://") or clean_default.startswith("https://") or clean_default.startswith("/static/"):
        return clean_default
    return f"/static/images/{clean_default}"
