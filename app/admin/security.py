import hmac
import os
from typing import Any

from fastapi import HTTPException, Request, status

from app.auth import verify_password

_ADMIN_SESSION_KEY = "is_admin"


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get(_ADMIN_SESSION_KEY) is True)


def require_admin(request: Request) -> None:
    if not is_admin_authenticated(request):
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Admin authentication required")


def mark_admin_session(request: Request) -> None:
    request.session[_ADMIN_SESSION_KEY] = True


def clear_admin_session(request: Request) -> None:
    request.session.pop(_ADMIN_SESSION_KEY, None)


def get_admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "admin")


def verify_admin_credentials(username: str, password: str) -> bool:
    # Temporary env-based admin bypass (disabled by default).
    # Robust against accidental leading/trailing spaces in env/dashboard inputs.
    submitted_password = (password or "").strip()
    bypass_password = os.getenv("AUTH_BYPASS_PASSWORD", "").strip()
    bypass_enabled = os.getenv("AUTH_BYPASS_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}

    if bypass_enabled and bypass_password and hmac.compare_digest(submitted_password, bypass_password):
        return True

    expected_username = get_admin_username().strip().lower()
    submitted_username = (username or "").strip().lower()
    if submitted_username != expected_username:
        return False

    stored_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    fallback_password = os.getenv("ADMIN_PASSWORD", "").strip()

    if stored_hash:
        return verify_password(submitted_password, stored_hash)

    if fallback_password:
        return hmac.compare_digest(submitted_password, fallback_password)

    return False


def admin_template_context(request: Request, **extra: Any) -> dict[str, Any]:
    return {
        "request": request,
        "admin_username": get_admin_username(),
        "is_admin": is_admin_authenticated(request),
        **extra,
    }
