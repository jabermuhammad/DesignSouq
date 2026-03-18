from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import build_daily_series, ensure_admin_tables
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

    def _safe_scalar(fn, default=0):
        try:
            return fn()
        except SQLAlchemyError:
            try:
                db.rollback()
            except Exception:
                pass
            return default

    total_designers = _safe_scalar(lambda: db.query(Designer).count(), 0)
    total_viewers = _safe_scalar(lambda: db.query(Viewer).count(), 0)
    total_users = total_designers + total_viewers
    total_projects = _safe_scalar(lambda: db.query(Project).count(), 0)
    def _count_reports(sql: str, params: dict | None = None) -> int:
        try:
            return int(db.execute(text(sql), params or {}).scalar_one())
        except SQLAlchemyError:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                ensure_admin_tables()
            except Exception:
                return 0
            try:
                return int(db.execute(text(sql), params or {}).scalar_one())
            except SQLAlchemyError:
                try:
                    db.rollback()
                except Exception:
                    pass
                return 0

    total_reports = _count_reports("SELECT COUNT(*) FROM admin_reports")

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    weekly_new_designers = _safe_scalar(
        lambda: db.query(func.count(Designer.id)).filter(Designer.created_at >= week_ago).scalar() or 0,
        0,
    )
    weekly_new_viewers = _safe_scalar(
        lambda: db.query(func.count(Viewer.id)).filter(Viewer.created_at >= week_ago).scalar() or 0,
        0,
    )
    weekly_new_projects = _safe_scalar(
        lambda: db.query(func.count(Project.id)).filter(Project.created_at >= week_ago).scalar() or 0,
        0,
    )
    def _reports_since(since: datetime) -> int:
        # Avoid sqlite-only datetime() to keep Postgres happy.
        # ISO strings compare correctly for SQLite TEXT timestamps.
        value = since.isoformat(sep=" ", timespec="seconds")
        return _count_reports(
            "SELECT COUNT(*) FROM admin_reports WHERE created_at >= :d",
            {"d": value},
        )

    weekly_new_reports = _reports_since(week_ago)

    monthly_new_designers = _safe_scalar(
        lambda: db.query(func.count(Designer.id)).filter(Designer.created_at >= month_ago).scalar() or 0,
        0,
    )
    monthly_new_viewers = _safe_scalar(
        lambda: db.query(func.count(Viewer.id)).filter(Viewer.created_at >= month_ago).scalar() or 0,
        0,
    )
    monthly_new_projects = _safe_scalar(
        lambda: db.query(func.count(Project.id)).filter(Project.created_at >= month_ago).scalar() or 0,
        0,
    )
    monthly_new_reports = _reports_since(month_ago)

    try:
        chart_data = build_daily_series(db, days=14)
    except SQLAlchemyError:
        try:
            db.rollback()
        except Exception:
            pass
        chart_data = {
            "labels": [],
            "visitors": [],
            "new_users": [],
            "new_projects": [],
            "reports": [],
        }

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
