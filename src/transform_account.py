"""
Transform a raw RapidAPI userInfo response into the clean dict used by the
ig_accounts table. Source shape: payload['result'][0]['user'].
"""


def _first_bio_link(user: dict) -> tuple[str | None, str | None]:
    links = user.get("bio_links") or []
    if not links:
        return None, None
    first = links[0]
    return first.get("link_type"), first.get("title")


def transform_user_info(payload: dict) -> dict:
    """
    Return:
        {
            "account": { ...ig_accounts row fields excluding profile_pic_local_path... },
            "profile_pic_url": str | None,   # downloader uses this, then writes path back
        }
    """
    result = payload.get("result") or []
    if not result:
        raise ValueError("userInfo response has no 'result' entries")

    user = result[0].get("user")
    if not user:
        raise ValueError("userInfo response is missing 'user'")

    bio_link_type, bio_link_title = _first_bio_link(user)

    account = {
        "account_type": "instagram",
        "account_id": str(user["id"]),
        "profile_type": user.get("profile_type"),
        "is_private": bool(user.get("is_private")),
        "username": user["username"],
        "full_name": user.get("full_name"),
        "followers": user.get("follower_count"),
        "following": user.get("following_count"),
        "published_posts": user.get("media_count"),
        "contact_method": user.get("business_contact_method"),
        "city": user.get("city_name"),
        "bio": user.get("biography"),
        "bio_link_type": bio_link_type,
        "bio_link_title": bio_link_title,
    }

    return {
        "account": account,
        "profile_pic_url": user.get("profile_pic_url"),
    }
