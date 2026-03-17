import hmac
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import hash_password, is_password_hashed, verify_password
from app.database import get_db
from app.models import Designer, Project, Viewer
from app.session_utils import build_auth_context
from app.services.image_storage import save_upload_image
from app.utils.images import resolve_image_url

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["image_url"] = resolve_image_url

router = APIRouter(prefix="/viewer")

def save_image(upload: UploadFile, folder: str = "profiles") -> str:
    return save_upload_image(upload, folder=folder)



def _password_matches(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    if stored_password == plain_password:
        return True
    return verify_password(plain_password, stored_password)


def _upgrade_password_if_plain(db: Session, viewer: Viewer, plain_password: str) -> None:
    if not is_password_hashed(viewer.password or ""):
        viewer.password = hash_password(plain_password)
        db.commit()
def ensure_viewer_owner(request: Request, viewer_id: int) -> None:
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")
    if user_type != "viewer" or user_id != viewer_id:
        raise HTTPException(status_code=403, detail="Only this viewer can open this dashboard")


@router.get("/{viewer_id}")
def dashboard(request: Request, viewer_id: int, db: Session = Depends(get_db)):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "viewer_dashboard.html",
        {
            "request": request,
            "viewer": viewer,
            "followed": viewer.following_designers,
            "liked": viewer.liked_projects,
            "wishlist": viewer.wishlist_projects,
            "auth": auth,
        },
    )



@router.post("/{viewer_id}/change-password")
def change_password(
    request: Request,
    viewer_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    cur = (current_password or "").strip()
    new = (new_password or "").strip()
    confirm = (confirm_password or "").strip()

    if not _password_matches(cur, viewer.password or ""):
        return RedirectResponse(url=f"/viewer/{viewer_id}?pwd_error=Current+password+is+incorrect", status_code=303)

    _upgrade_password_if_plain(db, viewer, cur)

    if len(new) < 8:
        return RedirectResponse(url=f"/viewer/{viewer_id}?pwd_error=New+password+must+be+at+least+8+characters", status_code=303)

    if new != confirm:
        return RedirectResponse(url=f"/viewer/{viewer_id}?pwd_error=Password+confirmation+does+not+match", status_code=303)

    if hmac.compare_digest(new, cur):
        return RedirectResponse(url=f"/viewer/{viewer_id}?pwd_error=New+password+must+be+different", status_code=303)

    viewer.password = hash_password(new)
    db.commit()
    return RedirectResponse(url=f"/viewer/{viewer_id}?pwd_ok=Password+updated+successfully", status_code=303)
@router.post("/{viewer_id}/profile-image")
def upload_profile_image(
    request: Request,
    viewer_id: int,
    profile_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")

    viewer.profile_image = save_image(profile_image)
    db.commit()
    return RedirectResponse(url=f"/viewer/{viewer_id}", status_code=303)


@router.post("/{viewer_id}/follow/{designer_id}")
def follow(request: Request, viewer_id: int, designer_id: int, db: Session = Depends(get_db)):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not viewer or not designer:
        raise HTTPException(status_code=404, detail="Viewer or designer not found")

    if designer in viewer.following_designers:
        viewer.following_designers.remove(designer)
    else:
        viewer.following_designers.append(designer)

    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/{viewer_id}/like/{project_id}")
def like(request: Request, viewer_id: int, project_id: int, db: Session = Depends(get_db)):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not viewer or not project:
        raise HTTPException(status_code=404, detail="Viewer or project not found")

    if project in viewer.liked_projects:
        viewer.liked_projects.remove(project)
    else:
        viewer.liked_projects.append(project)

    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/{viewer_id}/wishlist/{project_id}")
def wishlist(request: Request, viewer_id: int, project_id: int, db: Session = Depends(get_db)):
    ensure_viewer_owner(request, viewer_id)
    viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not viewer or not project:
        raise HTTPException(status_code=404, detail="Viewer or project not found")

    if project in viewer.wishlist_projects:
        viewer.wishlist_projects.remove(project)
    else:
        viewer.wishlist_projects.append(project)

    db.commit()
    return RedirectResponse(url="/", status_code=303)





