from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.admin._shared import templates
from app.admin.analytics import router as analytics_router
from app.admin.dashboard import router as dashboard_router
from app.admin.featured import router as featured_router
from app.admin.projects import router as projects_router
from app.admin.reports import router as reports_router
from app.admin.security import (
    admin_template_context,
    clear_admin_session,
    get_admin_username,
    is_admin_authenticated,
    mark_admin_session,
    verify_admin_credentials,
)
from app.admin.storage import ensure_admin_tables, get_admin_settings, set_admin_settings
from app.admin.users import router as users_router
from app.auth import hash_password
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin", tags=["admin"])

# keep admin extension self-contained and schema-compatible
ensure_admin_tables()


@router.get("")
@router.get("/")
def admin_root(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/log")
def admin_log_alias():
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login")
def admin_login_page(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    return templates.TemplateResponse(
        "admin/login.html",
        admin_template_context(request, login_error=None, login_page=True),
    )


@router.post("/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if verify_admin_credentials(username=username, password=password):
        mark_admin_session(request)
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    return templates.TemplateResponse(
        "admin/login.html",
        admin_template_context(request, login_error="Invalid admin credentials.", login_page=True),
        status_code=400,
    )


@router.post("/settings/password-helper")
def admin_password_helper(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    current = (current_password or "").strip()
    new = (new_password or "").strip()
    confirm = (confirm_password or "").strip()

    error = None
    generated_hash = ""
    helper_message = None

    if not verify_admin_credentials(get_admin_username(), current):
        error = "Current admin password is incorrect."
    elif len(new) < 8:
        error = "New password must be at least 8 characters."
    elif new != confirm:
        error = "Password confirmation does not match."
    else:
        generated_hash = hash_password(new)
        helper_message = "New hash generated. Set this as ADMIN_PASSWORD_HASH in Render env, then remove ADMIN_PASSWORD and disable bypass."

    return templates.TemplateResponse(
        "admin/settings.html",
        admin_template_context(
            request,
            active_page="settings",
            helper_error=error,
            helper_message=helper_message,
            generated_hash=generated_hash,
            footer_settings=get_admin_settings(db),
        ),
        status_code=400 if error else 200,
    )


@router.post("/settings/footer")
def admin_footer_settings(
    request: Request,
    facebook_url: str = Form(default=""),
    instagram_url: str = Form(default=""),
    behance_url: str = Form(default=""),
    support_email: str = Form(default=""),
    db: Session = Depends(get_db),
):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    updates = {
        "footer_facebook_url": facebook_url.strip(),
        "footer_instagram_url": instagram_url.strip(),
        "footer_behance_url": behance_url.strip(),
        "footer_support_email": support_email.strip(),
    }
    set_admin_settings(db, updates)

    return templates.TemplateResponse(
        "admin/settings.html",
        admin_template_context(
            request,
            active_page="settings",
            footer_settings=get_admin_settings(db),
            footer_message="Footer links updated successfully.",
        ),
    )


@router.get("/logout")
def admin_logout(request: Request):
    clear_admin_session(request)
    return RedirectResponse(url="/admin/login", status_code=303)


router.include_router(dashboard_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(reports_router)
router.include_router(featured_router)
router.include_router(analytics_router)
