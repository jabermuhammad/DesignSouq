from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import build_daily_series
from app.database import get_db
from app.models import Designer, Project, Viewer

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/analytics")
def analytics_page(request: Request, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    total_designers = db.query(Designer).count()
    total_viewers = db.query(Viewer).count()
    total_users = total_designers + total_viewers
    total_projects = db.query(Project).count()
    total_reports = int(db.execute(text("SELECT COUNT(*) FROM admin_reports")).scalar_one())

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    weekly_new_designers = db.query(func.count(Designer.id)).filter(Designer.created_at >= week_ago).scalar() or 0
    weekly_new_viewers = db.query(func.count(Viewer.id)).filter(Viewer.created_at >= week_ago).scalar() or 0
    weekly_new_projects = db.query(func.count(Project.id)).filter(Project.created_at >= week_ago).scalar() or 0
    weekly_new_reports = int(
        db.execute(
            text("SELECT COUNT(*) FROM admin_reports WHERE datetime(created_at) >= :d"),
            {"d": week_ago.isoformat(sep=" ", timespec="seconds")},
        ).scalar_one()
    )

    monthly_new_designers = db.query(func.count(Designer.id)).filter(Designer.created_at >= month_ago).scalar() or 0
    monthly_new_viewers = db.query(func.count(Viewer.id)).filter(Viewer.created_at >= month_ago).scalar() or 0
    monthly_new_projects = db.query(func.count(Project.id)).filter(Project.created_at >= month_ago).scalar() or 0
    monthly_new_reports = int(
        db.execute(
            text("SELECT COUNT(*) FROM admin_reports WHERE datetime(created_at) >= :d"),
            {"d": month_ago.isoformat(sep=" ", timespec="seconds")},
        ).scalar_one()
    )

    chart_data = build_daily_series(db, days=14)

    return templates.TemplateResponse(
        "admin/analytics.html",
        admin_template_context(
            request,
            active_page="analytics",
            metrics={
                "total_users": total_users,
                "total_designers": total_designers,
                "total_viewers": total_viewers,
                "total_projects": total_projects,
                "total_reports": total_reports,
                "weekly_new_designers": weekly_new_designers,
                "weekly_new_viewers": weekly_new_viewers,
                "weekly_new_projects": weekly_new_projects,
                "weekly_new_reports": weekly_new_reports,
                "monthly_new_designers": monthly_new_designers,
                "monthly_new_viewers": monthly_new_viewers,
                "monthly_new_projects": monthly_new_projects,
                "monthly_new_reports": monthly_new_reports,
            },
            chart_data=chart_data,
        ),
    )
