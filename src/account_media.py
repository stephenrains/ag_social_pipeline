"""Upload an account's profile picture to S3 under account_profile_images/{account_id}.{ext}"""
from . import storage

_PROFILE_PREFIX = "account_profile_images"


def upload_profile_pic(url: str, account_id: str) -> str:
    """Stream the profile pic to S3. Returns the S3 key."""
    ext = storage.extension_for(url, default_media_type=1) or ".jpg"
    key = f"{_PROFILE_PREFIX}/{account_id}{ext}"
    content_type = storage.content_type_for(url, default_media_type=1)
    return storage.upload_from_url(url, key, content_type)
