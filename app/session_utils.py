from fastapi import Request
from sqlalchemy.orm import Session

from app.models import Designer, Viewer


def build_auth_context(request: Request, db: Session) -> dict:
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    if not user_type or not user_id:
        return {
            "is_logged_in": False,
            "user_type": None,
            "user_id": None,
            "name": None,
            "avatar_url": None,
            "profile_url": None,
            "viewer_id": None,
        }

    if user_type == "designer":
        designer = db.query(Designer).filter(Designer.id == user_id).first()
        if not designer:
            request.session.clear()
            return {
                "is_logged_in": False,
                "user_type": None,
                "user_id": None,
                "name": None,
                "avatar_url": None,
                "profile_url": None,
                "viewer_id": None,
            }
        return {
            "is_logged_in": True,
            "user_type": "designer",
            "user_id": designer.id,
            "name": designer.full_name,
            "avatar_url": f"/static/images/{designer.profile_image or 'default-profile.svg'}",
            "profile_url": f"/designer/{designer.id}/dashboard",
            "viewer_id": None,
        }

    if user_type == "viewer":
        viewer = db.query(Viewer).filter(Viewer.id == user_id).first()
        if not viewer:
            request.session.clear()
            return {
                "is_logged_in": False,
                "user_type": None,
                "user_id": None,
                "name": None,
                "avatar_url": None,
                "profile_url": None,
                "viewer_id": None,
            }
        return {
            "is_logged_in": True,
            "user_type": "viewer",
            "user_id": viewer.id,
            "name": viewer.full_name,
            "avatar_url": f"/static/images/{viewer.profile_image or 'default-profile.svg'}",
            "profile_url": f"/viewer/{viewer.id}",
            "viewer_id": viewer.id,
        }

    request.session.clear()
    return {
        "is_logged_in": False,
        "user_type": None,
        "user_id": None,
        "name": None,
        "avatar_url": None,
        "profile_url": None,
        "viewer_id": None,
    }
