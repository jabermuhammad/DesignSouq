from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import ensure_admin_tables, get_featured_project_ids
from app.database import get_db
from app.models import Designer, Project

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/projects")
def projects_page(
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

    try:
        report_counts = {
            int(row[0]): int(row[1])
            for row in db.execute(
                text(
                    """
                    SELECT target_id, COUNT(*)
                    FROM admin_reports
                    WHERE target_type = 'project'
                    GROUP BY target_id
                    """
                )
            ).all()
        }
    except SQLAlchemyError:
        try:
            ensure_admin_tables()
        except Exception:
            report_counts = {}
        else:
            try:
                report_counts = {
                    int(row[0]): int(row[1])
                    for row in db.execute(
                        text(
                            """
                            SELECT target_id, COUNT(*)
                            FROM admin_reports
                            WHERE target_type = 'project'
                            GROUP BY target_id
                            """
                        )
                    ).all()
                }
            except SQLAlchemyError:
                report_counts = {}

    return templates.TemplateResponse(
        "admin/projects.html",
        admin_template_context(
            request,
            active_page="projects",
            projects=projects,
            q=clean_q,
            featured_ids=featured_ids,
            report_counts=report_counts,
        ),
    )


@router.post("/projects/{project_id}/delete")
def delete_project(request: Request, project_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()

    return RedirectResponse(url="/admin/projects", status_code=303)
