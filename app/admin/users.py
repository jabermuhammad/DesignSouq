from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.admin._shared import templates
from app.admin.security import admin_template_context, is_admin_authenticated
from app.admin.storage import get_ban_map, set_designer_ban
from app.database import get_db
from app.models import Designer, Viewer

router = APIRouter()


def _admin_only(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


@router.get("/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    ban_map = get_ban_map(db)
    banned_count = sum(1 for item in ban_map.values() if int(item.get("is_active", 0)) == 1)

    return templates.TemplateResponse(
        "admin/users.html",
        admin_template_context(
            request,
            active_page="users",
            designer_count=db.query(Designer).count(),
            viewer_count=db.query(Viewer).count(),
            banned_count=banned_count,
        ),
    )


@router.get("/designers")
def designers_page(
    request: Request,
    q: str = Query(default=""),
    db: Session = Depends(get_db),
):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    query = db.query(Designer)
    clean_q = q.strip()
    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            or_(
                Designer.full_name.ilike(like),
                Designer.username.ilike(like),
                Designer.email.ilike(like),
                Designer.skills.ilike(like),
            )
        )

    designers = query.order_by(Designer.created_at.desc()).all()
    ban_map = get_ban_map(db)

    return templates.TemplateResponse(
        "admin/designers.html",
        admin_template_context(
            request,
            active_page="designers",
            designers=designers,
            q=clean_q,
            ban_map=ban_map,
        ),
    )


@router.post("/designers/{designer_id}/ban")
def ban_designer(
    request: Request,
    designer_id: int,
    reason: str = Form(default=""),
    db: Session = Depends(get_db),
):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    if db.query(Designer).filter(Designer.id == designer_id).first():
        set_designer_ban(db, designer_id, reason or "Policy violation", True)

    return RedirectResponse(url="/admin/designers", status_code=303)


@router.post("/designers/{designer_id}/unban")
def unban_designer(request: Request, designer_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    if db.query(Designer).filter(Designer.id == designer_id).first():
        set_designer_ban(db, designer_id, "", False)

    return RedirectResponse(url="/admin/designers", status_code=303)


@router.post("/designers/{designer_id}/delete")
def delete_designer(request: Request, designer_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if designer:
        db.delete(designer)
        db.commit()

    return RedirectResponse(url="/admin/designers", status_code=303)


@router.get("/viewers")
def viewers_page(
    request: Request,
    q: str = Query(default=""),
    db: Session = Depends(get_db),
):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    query = db.query(Viewer)
    clean_q = q.strip()
    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            or_(
                Viewer.full_name.ilike(like),
                Viewer.username.ilike(like),
                Viewer.email.ilike(like),
            )
        )

    viewers = query.order_by(Viewer.created_at.desc()).all()

    return templates.TemplateResponse(
        "admin/viewers.html",
        admin_template_context(request, active_page="viewers", viewers=viewers, q=clean_q),
    )


@router.post("/viewers/{viewer_id}/delete")
def delete_viewer(request: Request, viewer_id: int, db: Session = Depends(get_db)):
    redirect = _admin_only(request)
    if redirect:
        return redirect

    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    if viewer:
        db.delete(viewer)
        db.commit()

    return RedirectResponse(url="/admin/viewers", status_code=303)
