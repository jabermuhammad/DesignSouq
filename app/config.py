import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "static", "uploads")
PROFILE_FOLDER = os.path.join(BASE_DIR, "..", "static", "profiles")
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "..", "static", "thumbnails")

for folder in [UPLOAD_FOLDER, PROFILE_FOLDER, THUMBNAIL_FOLDER]:
    os.makedirs(folder, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "designsouq-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
