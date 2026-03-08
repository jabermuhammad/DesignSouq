from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import get_featured_project_ids, set_project_featured
from app.database import get_db
from app.models import Designer, Project

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/featured")
def featured_page(
    request: Request,
    q: str = Query(default=""),
    db: Session = Depends(get_db),
):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    query = db.query(Project).join(Designer)
    clean_q = q.strip()
    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            or_(
                Project.title.ilike(like),
                Project.category.ilike(like),
                Project.tags.ilike(like),
                Designer.full_name.ilike(like),
            )
        )

    projects = query.order_by(Project.created_at.desc()).all()
    featured_ids = get_featured_project_ids(db)

    return templates.TemplateResponse(
        "admin/featured.html",
        admin_template_context(
            request,
            active_page="featured",
            projects=projects,
            featured_ids=featured_ids,
            q=clean_q,
        ),
    )


@router.post("/featured/{project_id}/mark")
def mark_featured(request: Request, project_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    if db.query(Project).filter(Project.id == project_id).first():
        set_project_featured(db, project_id, True)

    return RedirectResponse(url="/admin/featured", status_code=303)


@router.post("/featured/{project_id}/unmark")
def unmark_featured(request: Request, project_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    set_project_featured(db, project_id, False)
    return RedirectResponse(url="/admin/featured", status_code=303)
