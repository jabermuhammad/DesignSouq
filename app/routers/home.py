from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password, is_password_hashed, verify_password
from app.database import get_db
from app.models import Designer, Project, ProjectRating, Viewer
from app.password_reset import (
    consume_password_reset_token,
    create_password_reset_token,
    ensure_password_reset_table,
    validate_password_reset_token,
)
from app.session_utils import build_auth_context
from app.admin.storage import get_admin_settings
from app.services.image_storage import save_upload_image
from app.utils.images import resolve_image_url
from app.utils.email import send_reset_email

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
IMAGE_DIR = BASE_DIR / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
templates.env.globals["image_url"] = resolve_image_url

router = APIRouter()

ensure_password_reset_table()


def save_image(upload: UploadFile, folder: str = "projects") -> str:
    return save_upload_image(upload, folder=folder)


def _login_designer(request: Request, designer: Designer) -> RedirectResponse:
    request.session["user_type"] = "designer"
    request.session["user_id"] = designer.id
    return RedirectResponse(url=f"/designer/{designer.id}/dashboard", status_code=303)


def _login_viewer(request: Request, viewer: Viewer) -> RedirectResponse:
    request.session["user_type"] = "viewer"
    request.session["user_id"] = viewer.id
    return RedirectResponse(url=f"/viewer/{viewer.id}", status_code=303)


def _password_matches(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    if stored_password == plain_password:
        return True
    return verify_password(plain_password, stored_password)


def _upgrade_password_if_plain(db: Session, user: Designer | Viewer, plain_password: str) -> None:
    if not is_password_hashed(user.password or ""):
        user.password = hash_password(plain_password)
        db.commit()


def _resolve_actor_viewer(request: Request, db: Session) -> Viewer | None:
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    if user_type == "viewer" and user_id:
        return db.query(Viewer).filter(Viewer.id == int(user_id)).first()

    if user_type == "designer" and user_id:
        designer = db.query(Designer).filter(Designer.id == int(user_id)).first()
        if not designer:
            return None

        clean_email = (designer.email or "").strip().lower()
        actor = db.query(Viewer).filter(func.lower(Viewer.email) == clean_email).first()
        if actor:
            return actor

        actor = Viewer(
            full_name=designer.full_name,
            username=None,
            email=clean_email,
            password="",
        )
        db.add(actor)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            actor = db.query(Viewer).filter(func.lower(Viewer.email) == clean_email).first()
            if actor:
                return actor
            return None
        db.refresh(actor)
        return actor

    return None

@router.get("/")
def index(
    request: Request,
    q: str = Query(default=""),
    category: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = build_auth_context(request, db)

    query = db.query(Project).join(Designer)
    clean_q = q.strip()
    clean_category = category.strip()

    if clean_q:
        like = f"%{clean_q}%"
        query = query.filter(
            or_(
                Project.title.ilike(like),
                Project.tags.ilike(like),
                Project.category.ilike(like),
                Designer.skills.ilike(like),
            )
        )

    if clean_category:
        query = query.filter(Project.category.ilike(clean_category))

    projects = query.order_by(Project.created_at.desc()).limit(12).all()

    all_designers = db.query(Designer).all()
    all_projects = db.query(Project).all()

    suggestions: list[str] = []
    for designer in all_designers:
        for token in (designer.skills or "").split(","):
            skill = token.strip()
            if skill and skill not in suggestions:
                suggestions.append(skill)

    categories = sorted({item.category for item in all_projects if item.category})
    actor = _resolve_actor_viewer(request, db)
    actor_viewer_id = actor.id if actor else None
    actor_following_ids = [designer.id for designer in actor.following_designers] if actor else []
    actor_liked_project_ids = [project.id for project in actor.liked_projects] if actor else []
    actor_wishlist_ids = [project.id for project in actor.wishlist_projects] if actor else []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "projects": projects,
            "suggestions": suggestions[:5],
            "categories": categories,
            "q": clean_q,
            "selected_category": clean_category,
            "viewer_id": auth["viewer_id"],
            "actor_viewer_id": actor_viewer_id,
            "actor_following_ids": actor_following_ids,
            "actor_liked_project_ids": actor_liked_project_ids,
            "actor_wishlist_ids": actor_wishlist_ids,
            "session_user_type": request.session.get("user_type"),
            "session_user_id": request.session.get("user_id"),
            "auth": auth,
            "footer_settings": get_admin_settings(db),
        },
    )


@router.get("/api/suggestions")
def suggestion_api(q: str = Query(default=""), db: Session = Depends(get_db)):
    clean_q = q.strip().lower()
    designers = db.query(Designer).all()
    pool: list[str] = []

    for designer in designers:
        for token in (designer.skills or "").split(","):
            skill = token.strip()
            if not skill:
                continue
            if clean_q and clean_q not in skill.lower():
                continue
            if skill not in pool:
                pool.append(skill)

    return {"items": pool[:5]}


@router.get("/api/designer/{designer_id}/preview")
def preview_api(designer_id: int, db: Session = Depends(get_db)):
    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    total_projects = db.query(Project).filter(Project.designer_id == designer_id).count()
    return {
        "id": designer.id,
        "name": designer.full_name,
        "email": designer.email,
        "whatsapp": designer.whatsapp,
        "skills": designer.skills,
        "projects": total_projects,
        "followers": len(designer.followers),
        "address": designer.address,
        "profile_image": resolve_image_url(designer.profile_image, "default-profile.svg"),
        "profile_url": f"/designer/{designer.id}",
    }


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    auth = build_auth_context(request, db)
    return templates.TemplateResponse("login.html", {"request": request, "auth": auth, "error": None})


@router.post("/login")
def login(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    needle = identifier.strip()
    needle_lower = needle.lower()
    pwd = password.strip()

    if "@" in needle_lower:
        designers = db.query(Designer).filter(Designer.email == needle_lower).all()
        viewers = db.query(Viewer).filter(Viewer.email == needle_lower).all()
    else:
        designers = db.query(Designer).filter(Designer.username == needle_lower).all()
        viewers = db.query(Viewer).filter(Viewer.username == needle_lower).all()

    for designer in designers:
        if _password_matches(pwd, designer.password or ""):
            _upgrade_password_if_plain(db, designer, pwd)
            return _login_designer(request, designer)

    for viewer in viewers:
        if _password_matches(pwd, viewer.password or ""):
            _upgrade_password_if_plain(db, viewer, pwd)
            return _login_viewer(request, viewer)

    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "auth": auth, "error": "Invalid credentials. Please try again."},
        status_code=400,
    )


@router.get("/signup")
def signup_page(request: Request, db: Session = Depends(get_db)):
    auth = build_auth_context(request, db)
    return templates.TemplateResponse("signup.html", {"request": request, "auth": auth, "error": None})



@router.get("/forgot-password")
def forgot_password_page(request: Request, db: Session = Depends(get_db)):
    auth = build_auth_context(request, db)
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "auth": auth,
            "error": None,
            "message": None,
            "reset_link": None,
        },
    )


@router.post("/forgot-password")
def forgot_password_submit(
    request: Request,
    identifier: str = Form(...),
    db: Session = Depends(get_db),
):
    auth = build_auth_context(request, db)
    needle = (identifier or "").strip().lower()

    designer = db.query(Designer).filter(Designer.email == needle).first()
    viewer = db.query(Viewer).filter(Viewer.email == needle).first()

    reset_link = None
    if designer:
        token = create_password_reset_token(db, "designer", int(designer.id))
        reset_link = f"{str(request.base_url).rstrip('/')}/reset-password?token={token}"
        try:
            send_reset_email(designer.email, reset_link)
        except Exception:
            return templates.TemplateResponse(
                "forgot_password.html",
                {
                    "request": request,
                    "auth": auth,
                    "error": "Unable to send reset email right now. Please try again later.",
                    "message": None,
                    "reset_link": None,
                },
                status_code=500,
            )
    elif viewer:
        token = create_password_reset_token(db, "viewer", int(viewer.id))
        reset_link = f"{str(request.base_url).rstrip('/')}/reset-password?token={token}"
        try:
            send_reset_email(viewer.email, reset_link)
        except Exception:
            return templates.TemplateResponse(
                "forgot_password.html",
                {
                    "request": request,
                    "auth": auth,
                    "error": "Unable to send reset email right now. Please try again later.",
                    "message": None,
                    "reset_link": None,
                },
                status_code=500,
            )

    message = "If an account exists, a reset link has been generated."
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "auth": auth,
            "error": None,
            "message": message,
            "reset_link": None,
        },
    )


@router.get("/reset-password")
def reset_password_page(
    request: Request,
    token: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = build_auth_context(request, db)
    clean_token = (token or "").strip()
    valid = bool(clean_token and validate_password_reset_token(db, clean_token))

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "auth": auth,
            "token": clean_token,
            "valid_token": valid,
            "error": None,
            "message": None,
        },
    )


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    auth = build_auth_context(request, db)
    clean_token = (token or "").strip()
    pwd = (password or "").strip()
    confirm = (confirm_password or "").strip()

    payload = validate_password_reset_token(db, clean_token)
    if not payload:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "auth": auth,
                "token": clean_token,
                "valid_token": False,
                "error": "Reset link is invalid or expired.",
                "message": None,
            },
            status_code=400,
        )

    if len(pwd) < 8:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "auth": auth,
                "token": clean_token,
                "valid_token": True,
                "error": "Password must be at least 8 characters.",
                "message": None,
            },
            status_code=400,
        )

    if pwd != confirm:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "auth": auth,
                "token": clean_token,
                "valid_token": True,
                "error": "Password confirmation does not match.",
                "message": None,
            },
            status_code=400,
        )

    user_type, user_id = payload
    if user_type == "designer":
        user = db.query(Designer).filter(Designer.id == user_id).first()
    else:
        user = db.query(Viewer).filter(Viewer.id == user_id).first()

    if not user:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "auth": auth,
                "token": clean_token,
                "valid_token": False,
                "error": "Account not found for this reset link.",
                "message": None,
            },
            status_code=400,
        )

    user.password = hash_password(pwd)
    consume_password_reset_token(db, clean_token)
    db.commit()

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "auth": auth,
            "token": "",
            "valid_token": False,
            "error": None,
            "message": "Password reset successful. You can now log in.",
        },
    )
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.post("/action/follow/{designer_id}")
def action_follow(
    request: Request,
    designer_id: int,
    db: Session = Depends(get_db),
):
    actor = _resolve_actor_viewer(request, db)
    if not actor:
        return RedirectResponse(url="/login", status_code=303)

    current_user_type = request.session.get("user_type")
    current_user_id = request.session.get("user_id")
    if current_user_type == "designer" and str(current_user_id) == str(designer_id):
        return RedirectResponse(url=request.headers.get("referer") or "/", status_code=303)

    designer = db.query(Designer).filter(Designer.id == designer_id).first()
    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    if designer in actor.following_designers:
        actor.following_designers.remove(designer)
    else:
        actor.following_designers.append(designer)

    db.commit()
    return RedirectResponse(url=request.headers.get("referer") or "/", status_code=303)


@router.post("/action/like/{project_id}")
def action_like(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
):
    actor = _resolve_actor_viewer(request, db)
    if not actor:
        return RedirectResponse(url="/login", status_code=303)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project in actor.liked_projects:
        actor.liked_projects.remove(project)
    else:
        actor.liked_projects.append(project)

    db.commit()
    return RedirectResponse(url=request.headers.get("referer") or "/", status_code=303)


@router.post("/action/wishlist/{project_id}")
def action_wishlist(
    request: Request,
    project_id: int,
    rating: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    actor = _resolve_actor_viewer(request, db)
    if not actor:
        return RedirectResponse(url="/login", status_code=303)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project in actor.wishlist_projects:
        actor.wishlist_projects.remove(project)
    else:
        actor.wishlist_projects.append(project)

    if rating:
        try:
            rating_value = max(1, min(5, int(rating)))
        except (TypeError, ValueError):
            rating_value = None
        if rating_value:
            existing = (
                db.query(ProjectRating)
                .filter(ProjectRating.viewer_id == actor.id, ProjectRating.project_id == project.id)
                .first()
            )
            if existing:
                existing.rating = rating_value
            else:
                db.add(ProjectRating(viewer_id=actor.id, project_id=project.id, rating=rating_value))

    db.commit()
    return RedirectResponse(url=request.headers.get("referer") or "/", status_code=303)


@router.post("/signup/designer")
def signup_designer(
    request: Request,
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    whatsapp: str = Form(default=""),
    password: str = Form(...),
    skills: str = Form(...),
    bio: str = Form(default=""),
    profile_logo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    clean_email = email.strip().lower()
    clean_username = username.strip().lower()
    clean_whatsapp = whatsapp.strip()

    existing = db.query(Designer).filter(
        or_(Designer.email == clean_email, Designer.username == clean_username)
    ).first()
    existing_other_type = db.query(Viewer).filter(
        or_(Viewer.email == clean_email, Viewer.username == clean_username)
    ).first()
    if existing or existing_other_type:
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Email or username already registered."},
            status_code=400,
        )

    profile_image = "default-profile.svg"
    if profile_logo and profile_logo.filename:
        profile_image = save_image(profile_logo, folder="profiles")

    designer = Designer(
        full_name=full_name.strip(),
        username=clean_username,
        email=clean_email,
        password=hash_password(password.strip()),
        skills=skills.strip(),
        bio=bio.strip(),
        whatsapp=clean_whatsapp,
        address="",
        profile_image=profile_image,
    )
    db.add(designer)
    try:
        db.commit()
        db.refresh(designer)
    except IntegrityError:
        db.rollback()
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Email or username already registered."},
            status_code=400,
        )
    except Exception:
        db.rollback()
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Registration failed. Please try again."},
            status_code=400,
        )

    request.session["user_type"] = "designer"
    request.session["user_id"] = designer.id
    return RedirectResponse(url=f"/designer/{designer.id}/dashboard", status_code=303)


@router.post("/signup/viewer")
def signup_viewer(
    request: Request,
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    clean_email = email.strip().lower()
    clean_username = username.strip().lower()

    existing = db.query(Viewer).filter(
        or_(Viewer.email == clean_email, Viewer.username == clean_username)
    ).first()
    existing_other_type = db.query(Designer).filter(
        or_(Designer.email == clean_email, Designer.username == clean_username)
    ).first()
    if existing or existing_other_type:
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Email or username already registered."},
            status_code=400,
        )

    viewer = Viewer(
        full_name=full_name.strip(),
        username=clean_username,
        email=clean_email,
        password=hash_password(password.strip()),
    )
    db.add(viewer)
    try:
        db.commit()
        db.refresh(viewer)
    except IntegrityError:
        db.rollback()
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Email or username already registered."},
            status_code=400,
        )
    except Exception:
        db.rollback()
        auth = build_auth_context(request, db)
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "auth": auth, "error": "Registration failed. Please try again."},
            status_code=400,
        )

    request.session["user_type"] = "viewer"
    request.session["user_id"] = viewer.id
    return RedirectResponse(url=f"/viewer/{viewer.id}", status_code=303)





