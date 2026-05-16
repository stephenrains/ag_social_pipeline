"""Upload post media from the IG CDN to S3 under posts/{username}/{post_id}/{position}.{ext}"""
from . import storage


def upload_post_media(url: str, username: str, ig_post_id: str, position: int, media_type: int) -> str:
    """Stream the remote media file to S3. Returns the S3 key."""
    ext = storage.extension_for(url, default_media_type=media_type)
    key = f"posts/{username}/{ig_post_id}/{position}{ext}"
    content_type = storage.content_type_for(url, default_media_type=media_type)
    return storage.upload_from_url(url, key, content_type)
