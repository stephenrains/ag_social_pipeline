"""Download an account's profile picture to MEDIA_ROOT/account_profile_images/{account_id}.{ext}"""
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import MEDIA_ROOT

_PROFILE_DIR = MEDIA_ROOT / "account_profile_images"
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _extension_for(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in _IMAGE_EXTS else ".jpg"


def download_profile_pic(url: str, account_id: str) -> str:
    """Download the profile pic. Returns the absolute local path as a string."""
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    dest = _PROFILE_DIR / f"{account_id}{_extension_for(url)}"

    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)

    return str(dest)
