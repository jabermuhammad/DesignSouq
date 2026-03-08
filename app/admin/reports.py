from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import create_report, get_report, list_reports, set_designer_ban, update_report_status
from app.database import get_db
from app.models import Designer, Project

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/reports")
def reports_page(
    request: Request,
    status: str = Query(default=""),
    target_type: str = Query(default=""),
    db: Session = Depends(get_db),
):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    reports = list_reports(db, status=status.strip(), target_type=target_type.strip())

    designer_ids = [item["target_id"] for item in reports if item["target_type"] == "designer"]
    project_ids = [item["target_id"] for item in reports if item["target_type"] == "project"]

    designers = (
        db.query(Designer).filter(Designer.id.in_(designer_ids)).all() if designer_ids else []
    )
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []

    designer_map = {item.id: item for item in designers}
    project_map = {item.id: item for item in projects}

    return templates.TemplateResponse(
        "admin/reports.html",
        admin_template_context(
            request,
            active_page="reports",
            reports=reports,
            status=status.strip(),
            target_type=target_type.strip(),
            designer_map=designer_map,
            project_map=project_map,
        ),
    )


@router.post("/reports/{report_id}/ignore")
def ignore_report(request: Request, report_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    update_report_status(db, report_id, "ignored", "Ignored by admin")
    return RedirectResponse(url="/admin/reports", status_code=303)


@router.post("/reports/{report_id}/ban")
def ban_from_report(request: Request, report_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    report = get_report(db, report_id)
    if report:
        if report["target_type"] == "designer":
            set_designer_ban(db, int(report["target_id"]), report["reason"], True)
            update_report_status(db, report_id, "actioned", "Designer banned")
        elif report["target_type"] == "project":
            project = db.query(Project).filter(Project.id == int(report["target_id"])).first()
            if project:
                set_designer_ban(db, int(project.designer_id), report["reason"], True)
                update_report_status(db, report_id, "actioned", "Project owner banned")

    return RedirectResponse(url="/admin/reports", status_code=303)


@router.post("/reports/{report_id}/remove-project")
def remove_project_from_report(request: Request, report_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    report = get_report(db, report_id)
    if report and report["target_type"] == "project":
        project = db.query(Project).filter(Project.id == int(report["target_id"])).first()
        if project:
            db.delete(project)
            db.commit()
            update_report_status(db, report_id, "actioned", "Project removed")

    return RedirectResponse(url="/admin/reports", status_code=303)


@router.post("/reports/submit/project/{project_id}")
def submit_project_report(
    project_id: int,
    reason: str = Form(...),
    reporter_name: str = Form(default=""),
    reporter_email: str = Form(default=""),
    db: Session = Depends(get_db),
):
    if not db.query(Project).filter(Project.id == project_id).first():
        return RedirectResponse(url="/", status_code=303)

    create_report(
        db,
        target_type="project",
        target_id=project_id,
        reason=reason,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
    )
    return RedirectResponse(url="/", status_code=303)


@router.post("/reports/submit/designer/{designer_id}")
def submit_designer_report(
    designer_id: int,
    reason: str = Form(...),
    reporter_name: str = Form(default=""),
    reporter_email: str = Form(default=""),
    db: Session = Depends(get_db),
):
    if not db.query(Designer).filter(Designer.id == designer_id).first():
        return RedirectResponse(url="/", status_code=303)

    create_report(
        db,
        target_type="designer",
        target_id=designer_id,
        reason=reason,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
    )
    return RedirectResponse(url="/", status_code=303)
