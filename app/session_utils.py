from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Designer, Viewer
from app.utils.images import resolve_image_url


def _empty_auth_context() -> dict:
    return {
        "is_logged_in": False,
        "user_type": None,
        "user_id": None,
        "name": None,
        "avatar_url": None,
        "profile_url": None,
        "viewer_id": None,
    }


def build_auth_context(request: Request, db: Session) -> dict:
    user_type = request.session.get("user_type")
    user_id_raw = request.session.get("user_id")

    if not user_type or user_id_raw in (None, ""):
        return _empty_auth_context()

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        request.session.clear()
        return _empty_auth_context()

    if user_type == "designer":
        designer = db.query(Designer).filter(Designer.id == user_id).first()
        if not designer:
            request.session.clear()
            return _empty_auth_context()
        return {
            "is_logged_in": True,
            "user_type": "designer",
            "user_id": designer.id,
            "name": designer.full_name,
            "avatar_url": resolve_image_url(designer.profile_image, "default-profile.svg"),
            "profile_url": f"/designer/{designer.id}/dashboard",
            "viewer_id": None,
        }

    if user_type == "viewer":
        viewer = db.query(Viewer).filter(Viewer.id == user_id).first()
        if not viewer:
            request.session.clear()
            return _empty_auth_context()
        return {
            "is_logged_in": True,
            "user_type": "viewer",
            "user_id": viewer.id,
            "name": viewer.full_name,
            "avatar_url": resolve_image_url(viewer.profile_image, "default-profile.svg"),
            "profile_url": f"/viewer/{viewer.id}",
            "viewer_id": viewer.id,
        }

    request.session.clear()
    return _empty_auth_context()
