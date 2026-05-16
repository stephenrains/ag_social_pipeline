"""
S3 storage layer for media files.

New ingestion code writes only to S3. The DB stores object *keys* (not URLs),
e.g. `posts/fourtillfourcafe/3896.../0.jpg`. The frontend prepends
`S3_PUBLIC_BASE_URL` to build the final image URL.
"""
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

import boto3
import requests
from botocore.client import Config

from .config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    S3_BUCKET,
)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
_VIDEO_EXTS = {".mp4", ".mov", ".m4v"}

_s3_client = None


def get_client():
    """Lazy boto3 S3 client; raises clearly if AWS config is missing."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    missing = [
        name for name, val in [
            ("AWS_REGION", AWS_REGION),
            ("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID),
            ("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY),
            ("S3_BUCKET", S3_BUCKET),
        ]
        if not val
    ]
    if missing:
        raise RuntimeError(f"S3 not configured; missing env vars: {', '.join(missing)}")
    _s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )
    return _s3_client


def content_type_for(filename_or_url: str, default_media_type: int | None = None) -> str:
    """Pick a MIME type from a file extension. Falls back by media_type (1=photo, 2=video)."""
    path = urlparse(filename_or_url).path if "://" in filename_or_url else filename_or_url
    ext = Path(path).suffix.lower()
    if ext in _CONTENT_TYPES:
        return _CONTENT_TYPES[ext]
    if default_media_type == 1:
        return "image/jpeg"
    if default_media_type == 2:
        return "video/mp4"
    return "application/octet-stream"


def extension_for(url_or_path: str, default_media_type: int | None = None) -> str:
    """Pick a file extension from a URL or path. Falls back by media_type."""
    path = urlparse(url_or_path).path if "://" in url_or_path else url_or_path
    ext = Path(path).suffix.lower()
    if ext in _IMAGE_EXTS or ext in _VIDEO_EXTS:
        return ext
    if default_media_type == 1:
        return ".jpg"
    if default_media_type == 2:
        return ".mp4"
    return ""


def upload_fileobj(key: str, fileobj: BinaryIO, content_type: str) -> str:
    """Upload an open binary file-like object. Returns the key."""
    client = get_client()
    client.upload_fileobj(
        Fileobj=fileobj,
        Bucket=S3_BUCKET,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )
    return key


def upload_file(key: str, local_path: str, content_type: str) -> str:
    """Upload a file from local disk. Returns the key."""
    client = get_client()
    client.upload_file(
        Filename=local_path,
        Bucket=S3_BUCKET,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )
    return key


def upload_from_url(url: str, key: str, content_type: str) -> str:
    """Stream a remote URL straight into S3 without buffering to disk. Returns the key."""
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        resp.raw.decode_content = True  # transparent gzip handling if upstream uses it
        upload_fileobj(key, resp.raw, content_type)
    return key
