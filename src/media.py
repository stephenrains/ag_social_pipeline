"""Download post media to MEDIA_ROOT/{username}/{ig_post_id}/{position}.{ext}"""
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import MEDIA_ROOT


_EXT_BY_MEDIA_TYPE = {1: ".jpg", 2: ".mp4"}


def _extension_for(url: str, media_type: int) -> str:
    """Pick an extension from the URL path, falling back to media_type default."""
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".mp4", ".mov", ".m4v"}:
        return suffix
    return _EXT_BY_MEDIA_TYPE.get(media_type, "")


def download_media(url: str, username: str, ig_post_id: str, position: int, media_type: int) -> str:
    """Download one media file. Returns the absolute local path as a string."""
    folder = MEDIA_ROOT / username / ig_post_id
    folder.mkdir(parents=True, exist_ok=True)

    ext = _extension_for(url, media_type)
    dest = folder / f"{position}{ext}"

    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)

    return str(dest)
