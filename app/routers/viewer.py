from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Designer, Project, Viewer
from app.session_utils import build_auth_context

BASE_DIR = Path(__file__).resolve().parents[1]
IMAGE_DIR = BASE_DIR / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/viewer")

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}


def save_image(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    content_type = (upload.content_type or "").lower()

    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    filename = f"img_{uuid4().hex[:12]}{suffix}"
    target = IMAGE_DIR / filename
    with target.open("wb") as out:
        out.write(upload.file.read())
    return filename


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


