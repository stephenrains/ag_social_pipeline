import time

import requests

from .config import RAPIDAPI_HOST, RAPIDAPI_KEY

POSTS_URL = f"https://{RAPIDAPI_HOST}/api/instagram/posts"
USER_INFO_URL = f"https://{RAPIDAPI_HOST}/api/instagram/userInfo"

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4
_BASE_BACKOFF_S = 2.0  # 2s, 4s, 8s between attempts


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }


def _post_with_retry(url: str, json_payload: dict) -> dict:
    """POST with exponential backoff on transient errors (5xx, 429, connection issues)."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json=json_payload, headers=_headers(), timeout=30)
            if resp.status_code in _RETRY_STATUSES and attempt < _MAX_ATTEMPTS:
                wait = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                print(f"  upstream {resp.status_code}; retry {attempt}/{_MAX_ATTEMPTS - 1} in {wait:.1f}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            if attempt < _MAX_ATTEMPTS:
                wait = _BASE_BACKOFF_S * (2 ** (attempt - 1))
                print(f"  network error ({e.__class__.__name__}); retry {attempt}/{_MAX_ATTEMPTS - 1} in {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise
    if last_exc:
        raise last_exc
    # Loop fell through with a retryable status on the final attempt.
    raise requests.HTTPError(f"upstream still failing after {_MAX_ATTEMPTS} attempts: {url}")


def fetch_posts_page(username: str, max_id: str = "") -> dict:
    """Fetch a single page of posts for the given username."""
    return _post_with_retry(POSTS_URL, {"username": username, "maxId": max_id})


def fetch_user_info(username: str) -> dict:
    """Fetch the userInfo payload for the given username."""
    return _post_with_retry(USER_INFO_URL, {"username": username})
