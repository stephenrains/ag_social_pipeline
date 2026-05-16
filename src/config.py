import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"]

_DATABASE_URL_RAW = os.environ.get("DATABASE_URL", "").strip()

# If DATABASE_URL is set (e.g. Render's External/Internal URL), use it.
# Otherwise build one from individual fields (local dev style).
if _DATABASE_URL_RAW:
    DB_HOST = DB_PORT = DB_NAME = DB_USER = DB_PASSWORD = ""
else:
    DB_HOST = os.environ["DB_HOST"]
    DB_PORT = os.environ["DB_PORT"]
    DB_NAME = os.environ["DB_NAME"]
    DB_USER = os.environ["DB_USER"]
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

# Legacy local media root — used only by the backfill script. Optional in cloud envs.
_media_root = os.environ.get("MEDIA_ROOT")
MEDIA_ROOT = Path(_media_root) if _media_root else None

API_TOKEN = os.environ.get("API_TOKEN", "")

AWS_REGION = os.environ.get("AWS_REGION", "")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_PUBLIC_BASE_URL = os.environ.get("S3_PUBLIC_BASE_URL", "").rstrip("/")

def _to_sqlalchemy_url(raw: str) -> str:
    """SQLAlchemy needs the psycopg driver suffix; Render gives bare postgresql://."""
    if raw.startswith("postgresql+"):
        return raw
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    return raw


if _DATABASE_URL_RAW:
    DB_URL = _to_sqlalchemy_url(_DATABASE_URL_RAW)
else:
    DB_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
