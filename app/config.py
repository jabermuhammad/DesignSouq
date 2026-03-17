import os

def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_load_env_file(os.path.join(BASE_DIR, "..", ".env"))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "static", "uploads")
PROFILE_FOLDER = os.path.join(BASE_DIR, "..", "static", "profiles")
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "..", "static", "thumbnails")

for folder in [UPLOAD_FOLDER, PROFILE_FOLDER, THUMBNAIL_FOLDER]:
    os.makedirs(folder, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "designsouq-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
