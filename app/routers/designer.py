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

router = APIRouter(prefix="/designer")


def save_image(upload: UploadFile, folder: str = "projects") -> str:
    return save_upload_image(upload, folder=folder)



def _password_matches(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    if stored_password == plain_password:
        return True
    return verify_password(plain_password, stored_password)


def _upgrade_password_if_plain(db: Session, designer: Designer, plain_password: str) -> None:
    if not is_password_hashed(designer.password or ""):
        designer.password = hash_password(plain_password)
        db.commit()
def ensure_designer_owner(request: Request, designer_id: int) -> None:
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")
    if user_type != "designer" or user_id != designer_id:
        raise HTTPException(status_code=403, detail="Only this designer can modify this profile")


def _normalize_url(url: str) -> str:
    clean = (url or "").strip()
    if not clean:
        return ""
    lower = clean.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return clean
    return f"https://{clean}"


@router.get("/{designer_id}/dashboard")
def dashboard(request: Request, designer_id: int, db: Session = Depends(get_db)):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    projects = (
        db.query(Project)
        .filter(Project.designer_id == designer_id)
        .order_by(Project.created_at.desc())
        .all()
    )

    total_likes = sum(len(item.liked_by) for item in projects)
    total_saves = sum(len(item.wishlisted_by) for item in projects)
    analytics = {
        "project_count": len(projects),
        "total_likes": total_likes,
        "total_saves": total_saves,
        "total_views": 0,
    }

    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "designer_dashboard.html",
        {"request": request, "designer": designer, "projects": projects[:12], "analytics": analytics, "auth": auth},
    )



@router.post("/{designer_id}/change-password")
def change_password(
    request: Request,
    designer_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    cur = (current_password or "").strip()
    new = (new_password or "").strip()
    confirm = (confirm_password or "").strip()

    if not _password_matches(cur, designer.password or ""):
        return RedirectResponse(url=f"/designer/{designer_id}/dashboard?pwd_error=Current+password+is+incorrect", status_code=303)

    _upgrade_password_if_plain(db, designer, cur)

    if len(new) < 8:
        return RedirectResponse(url=f"/designer/{designer_id}/dashboard?pwd_error=New+password+must+be+at+least+8+characters", status_code=303)

    if new != confirm:
        return RedirectResponse(url=f"/designer/{designer_id}/dashboard?pwd_error=Password+confirmation+does+not+match", status_code=303)

    if hmac.compare_digest(new, cur):
        return RedirectResponse(url=f"/designer/{designer_id}/dashboard?pwd_error=New+password+must+be+different", status_code=303)

    designer.password = hash_password(new)
    db.commit()
    return RedirectResponse(url=f"/designer/{designer_id}/dashboard?pwd_ok=Password+updated+successfully", status_code=303)
@router.get("/{designer_id}")
def profile(request: Request, designer_id: int, db: Session = Depends(get_db)):
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    projects = (
        db.query(Project)
        .filter(Project.designer_id == designer_id)
        .order_by(Project.created_at.desc())
        .limit(12)
        .all()
    )

    auth = build_auth_context(request, db)
    viewer_id = auth.get("viewer_id")
    is_following = False
    if viewer_id:
        viewer = db.query(Viewer).filter(Viewer.id == viewer_id).first()
        if viewer:
            is_following = any(item.id == designer_id for item in viewer.following_designers)

    followers_count = len(designer.followers)

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "designer": designer,
            "projects": projects,
            "auth": auth,
            "is_owner": auth.get("user_type") == "designer" and auth.get("user_id") == designer_id,
            "is_following": is_following,
            "followers_count": followers_count,
        },
    )


@router.post("/{designer_id}/profile-info")
def update_profile_info(
    request: Request,
    designer_id: int,
    whatsapp: str = Form(default=""),
    address: str = Form(default=""),
    skills: str = Form(default=""),
    bio: str = Form(default=""),
    website_url: str = Form(default=""),
    facebook_url: str = Form(default=""),
    instagram_url: str = Form(default=""),
    behance_url: str = Form(default=""),
    dribbble_url: str = Form(default=""),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    designer.whatsapp = whatsapp.strip()
    designer.address = address.strip()
    designer.skills = skills.strip()
    designer.bio = bio.strip()
    designer.website_url = _normalize_url(website_url)
    designer.facebook_url = _normalize_url(facebook_url)
    designer.instagram_url = _normalize_url(instagram_url)
    designer.behance_url = _normalize_url(behance_url)
    designer.dribbble_url = _normalize_url(dribbble_url)
    db.commit()

    return RedirectResponse(url=f"/designer/{designer_id}", status_code=303)


@router.post("/{designer_id}/cover")
def upload_cover(
    request: Request,
    designer_id: int,
    cover_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    designer.cover_image = save_image(cover_image, folder="covers")
    db.commit()
    return RedirectResponse(url=f"/designer/{designer_id}", status_code=303)


@router.post("/{designer_id}/profile-image")
def upload_profile_image(
    request: Request,
    designer_id: int,
    profile_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    designer.profile_image = save_image(profile_image, folder="profiles")
    db.commit()
    return RedirectResponse(url=f"/designer/{designer_id}", status_code=303)


@router.get("/{designer_id}/upload")
def upload_page(request: Request, designer_id: int, db: Session = Depends(get_db)):
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "upload_project.html",
        {"request": request, "designer": designer, "project": None, "auth": auth},
    )


@router.post("/{designer_id}/upload")
def upload_project(
    request: Request,
    designer_id: int,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    tags: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    filename = save_image(image, folder="projects")
    project = Project(
        designer_id=designer_id,
        title=title.strip(),
        description=description.strip(),
        category=category.strip(),
        tags=tags.strip(),
        image_filename=filename,
    )
    db.add(project)
    db.commit()
    return RedirectResponse(url=f"/designer/{designer_id}/dashboard", status_code=303)


@router.get("/{designer_id}/project/{project_id}/edit")
def edit_page(request: Request, designer_id: int, project_id: int, db: Session = Depends(get_db)):
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    project = db.query(Project).filter(Project.id == project_id, Project.designer_id == designer_id).first()
    if not designer or not project:
        raise HTTPException(status_code=404, detail="Project not found")

    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "upload_project.html",
        {"request": request, "designer": designer, "project": project, "auth": auth},
    )


@router.post("/{designer_id}/project/{project_id}/edit")
def edit_project(
    request: Request,
    designer_id: int,
    project_id: int,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    tags: str = Form(...),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    ensure_designer_owner(request, designer_id)
    project = db.query(Project).filter(Project.id == project_id, Project.designer_id == designer_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.title = title.strip()
    project.description = description.strip()
    project.category = category.strip()
    project.tags = tags.strip()

    if image and image.filename:
        project.image_filename = save_image(image, folder="projects")

    db.commit()
    return RedirectResponse(url=f"/designer/{designer_id}/dashboard", status_code=303)




