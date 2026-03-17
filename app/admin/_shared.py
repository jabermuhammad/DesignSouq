from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.utils.images import resolve_image_url

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["image_url"] = resolve_image_url
