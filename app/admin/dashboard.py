from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import get_ban_map, get_featured_project_ids
from app.database import get_db
from app.models import Designer, Project, Viewer, viewer_follows, viewer_likes, viewer_wishlist

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    total_designers = db.query(Designer).count()
    total_viewers = db.query(Viewer).count()
    total_projects = db.query(Project).count()

    total_likes = db.execute(select(func.count()).select_from(viewer_likes)).scalar_one()
    total_followers = db.execute(select(func.count()).select_from(viewer_follows)).scalar_one()
    total_wishlist = db.execute(select(func.count()).select_from(viewer_wishlist)).scalar_one()

    ban_map = get_ban_map(db)
    banned_designers = sum(1 for item in ban_map.values() if int(item.get("is_active", 0)) == 1)
    featured_count = len(get_featured_project_ids(db))
    open_reports = int(
        db.execute(text("SELECT COUNT(*) FROM admin_reports WHERE status = 'open'"))
        .scalar_one()
    )

    recent_designers = db.query(Designer).order_by(Designer.created_at.desc()).limit(8).all()
    recent_viewers = db.query(Viewer).order_by(Viewer.created_at.desc()).limit(8).all()
    recent_projects = (
        db.query(Project)
        .join(Designer)
        .order_by(Project.created_at.desc())
        .limit(8)
        .all()
    )

    recent_reports = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT id, target_type, target_id, reason, status, created_at
                FROM admin_reports
                ORDER BY created_at DESC, id DESC
                LIMIT 8
                """
            )
        ).mappings().all()
    ]

    return templates.TemplateResponse(
        "admin/dashboard.html",
        admin_template_context(
            request,
            active_page="dashboard",
            stats={
                "total_designers": total_designers,
                "total_viewers": total_viewers,
                "total_projects": total_projects,
                "total_likes": total_likes,
                "total_followers": total_followers,
                "total_wishlist": total_wishlist,
                "banned_designers": banned_designers,
                "featured_projects": featured_count,
                "open_reports": open_reports,
            },
            recent_designers=recent_designers,
            recent_viewers=recent_viewers,
            recent_projects=recent_projects,
            recent_reports=recent_reports,
        ),
    )


@router.get("/settings")
def settings_page(request: Request):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "admin/settings.html",
        admin_template_context(request, active_page="settings"),
    )
