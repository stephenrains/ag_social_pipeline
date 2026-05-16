"""
Transform a raw Instagram post `node` (from result.edges[].node) into the
clean shapes used by the DB and media downloader.

See raw_data/pipeline_process_overview.txt for the source-of-truth logic.
"""
from datetime import datetime, timezone


def _safe_get(d, *keys):
    """Walk nested dict/list keys, returning None if any step is missing."""
    cur = d
    for k in keys:
        if cur is None:
            return None
        try:
            cur = cur[k]
        except (KeyError, IndexError, TypeError):
            return None
    return cur


def _first_image_candidate(image_versions2: dict | None):
    candidates = _safe_get(image_versions2, "candidates")
    if not candidates:
        return None
    return candidates[0]


def _media_items_from_node(node: dict) -> list[dict]:
    """
    Return list of {position, media_type, url, height, width} for this post's media.
    `media_type` here is 1 (photo) or 2 (video) — carousel parent type 8 is exploded.
    """
    items: list[dict] = []
    post_type = node.get("media_type")

    if post_type == 1:
        cand = _first_image_candidate(node.get("image_versions2"))
        if cand and cand.get("url"):
            items.append({
                "position": 0,
                "media_type": 1,
                "url": cand["url"],
                "height": cand.get("height"),
                "width": cand.get("width"),
            })

    elif post_type == 2:
        vvs = node.get("video_versions")
        if vvs:
            v = vvs[0]
            # Video versions usually carry their own width/height; fall back to image thumb.
            height = v.get("height")
            width = v.get("width")
            if height is None or width is None:
                cand = _first_image_candidate(node.get("image_versions2"))
                if cand:
                    height = height or cand.get("height")
                    width = width or cand.get("width")
            if v.get("url"):
                items.append({
                    "position": 0,
                    "media_type": 2,
                    "url": v["url"],
                    "height": height,
                    "width": width,
                })

    elif post_type == 8:
        carousel = node.get("carousel_media") or []
        for idx, child in enumerate(carousel):
            child_type = child.get("media_type")
            if child_type == 1:
                cand = _first_image_candidate(child.get("image_versions2"))
                if cand and cand.get("url"):
                    items.append({
                        "position": idx,
                        "media_type": 1,
                        "url": cand["url"],
                        "height": cand.get("height"),
                        "width": cand.get("width"),
                    })
            elif child_type == 2:
                vvs = child.get("video_versions")
                if vvs:
                    v = vvs[0]
                    if v.get("url"):
                        items.append({
                            "position": idx,
                            "media_type": 2,
                            "url": v["url"],
                            "height": v.get("height"),
                            "width": v.get("width"),
                        })

    return items


def _users_tagged(node: dict) -> list[str]:
    tagged = _safe_get(node, "usertags", "in") or []
    out: list[str] = []
    seen: set[str] = set()
    for entry in tagged:
        u = _safe_get(entry, "user", "username")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _coauthors(node: dict) -> list[str]:
    coas = node.get("coauthor_producers") or []
    out: list[str] = []
    seen: set[str] = set()
    for c in coas:
        u = c.get("username")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def transform_node(node: dict, post_owner_username: str) -> dict:
    """
    Return a dict:
        {
            "post":        { ... ig_posts row fields ... },
            "media":       [ {position, media_type, url, height, width}, ... ],
            "users_tagged": [username, ...],
            "coauthors":    [username, ...],
        }

    `media` items still have `url` instead of `local_path` — the downloader fills that in.
    """
    post_type = node.get("media_type")
    caption = _safe_get(node, "caption", "text")

    if node.get("like_and_view_counts_disabled") is True:
        likes = -1
        views = -1
    else:
        likes = node.get("like_count")
        views = node.get("view_count")
        likes = -1 if likes is None else int(likes)
        views = -1 if views is None else int(views)

    if node.get("comments_disabled") is True:
        comments = -1
    else:
        comments = node.get("comment_count")
        comments = -1 if comments is None else int(comments)

    taken_at_epoch = node.get("taken_at")
    taken_at = (
        datetime.fromtimestamp(taken_at_epoch, tz=timezone.utc)
        if isinstance(taken_at_epoch, (int, float))
        else None
    )

    post = {
        "ig_post_id": node["id"],
        "post_owner_username": post_owner_username,
        "caption": caption,
        "post_type": post_type,
        "likes": likes,
        "views": views,
        "comments": comments,
        "paid_partnership": bool(node.get("is_paid_partnership")),
        "taken_at": taken_at,
    }

    return {
        "post": post,
        "media": _media_items_from_node(node),
        "users_tagged": _users_tagged(node),
        "coauthors": _coauthors(node),
    }
