"""
Fetch Instagram posts for a username with pagination, download media locally,
and upsert into Postgres. Stops at max_posts or max_pages, whichever comes first.

Usage:
    python get_ig_posts.py <username>
"""
import sys
import time

from src.db import get_engine, upsert_post
from src.ig_api import fetch_posts_page
from src.media import download_media
from src.transform import transform_node

DEFAULT_MAX_POSTS = 96
DEFAULT_MAX_PAGES = 8
SLEEP_BETWEEN_PAGES_S = 1.0


def _process_edge(engine, username: str, edge: dict) -> tuple[bool, int, bool]:
    """Process one edge. Returns (post_ok, media_downloaded, errored)."""
    node = edge.get("node") or {}
    ig_post_id = node.get("id")
    if not ig_post_id:
        print("  skip: node missing id")
        return False, 0, True

    try:
        t = transform_node(node, post_owner_username=username)
    except Exception as e:
        print(f"  skip {ig_post_id}: transform error: {e}")
        return False, 0, True

    media_rows = []
    try:
        for item in t["media"]:
            local_path = download_media(
                url=item["url"],
                username=username,
                ig_post_id=ig_post_id,
                position=item["position"],
                media_type=item["media_type"],
            )
            media_rows.append({
                "position": item["position"],
                "media_type": item["media_type"],
                "local_path": local_path,
                "height": item["height"],
                "width": item["width"],
            })
    except Exception as e:
        print(f"  skip {ig_post_id}: media download failed: {e}")
        return False, 0, True

    try:
        upsert_post(
            engine,
            post=t["post"],
            media=media_rows,
            users_tagged=t["users_tagged"],
            coauthors=t["coauthors"],
        )
        print(f"  ok {ig_post_id} (type={t['post']['post_type']}, media={len(media_rows)})")
        return True, len(media_rows), False
    except Exception as e:
        print(f"  fail {ig_post_id}: db upsert: {e}")
        return False, 0, True


def process_username(
    username: str,
    max_posts: int = DEFAULT_MAX_POSTS,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> dict:
    """Run the posts ingestion for one username. Returns a summary dict."""
    engine = get_engine()

    max_id = ""
    posts_ok = 0
    media_ok = 0
    errors = 0
    pages_fetched = 0
    last_page_info: dict = {}
    stop_reason = "completed"

    for page_num in range(1, max_pages + 1):
        print(f"\nFetching page {page_num} for @{username} (max_id={max_id!r})...")
        try:
            payload = fetch_posts_page(username, max_id=max_id)
        except Exception as e:
            print(f"Page {page_num} fetch failed after retries: {e}; stopping.")
            stop_reason = f"fetch_failed: {e}"
            break
        pages_fetched = page_num

        result = payload.get("result") or {}
        edges = result.get("edges") or []
        last_page_info = result.get("page_info") or {}
        print(f"Received {len(edges)} posts on this page.")

        for edge in edges:
            if posts_ok + errors >= max_posts:
                break
            ok, mdl, err = _process_edge(engine, username, edge)
            if ok:
                posts_ok += 1
                media_ok += mdl
            if err:
                errors += 1

        if posts_ok + errors >= max_posts:
            print(f"Reached max_posts cap ({max_posts}); stopping.")
            stop_reason = "max_posts_reached"
            break
        if not last_page_info.get("has_next_page"):
            print("No more pages available; stopping.")
            stop_reason = "no_more_pages"
            break

        next_cursor = last_page_info.get("end_cursor")
        if not next_cursor:
            print("has_next_page=true but no end_cursor; stopping.")
            stop_reason = "missing_cursor"
            break
        max_id = next_cursor

        if page_num < max_pages:
            time.sleep(SLEEP_BETWEEN_PAGES_S)
    else:
        stop_reason = "max_pages_reached"

    summary = {
        "username": username,
        "pages_fetched": pages_fetched,
        "posts_upserted": posts_ok,
        "media_downloaded": media_ok,
        "errors": errors,
        "has_next_page": last_page_info.get("has_next_page"),
        "end_cursor": last_page_info.get("end_cursor"),
        "stop_reason": stop_reason,
    }
    print(f"\nDone. {summary}")
    return summary


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python get_ig_posts.py <username>", file=sys.stderr)
        sys.exit(1)
    process_username(sys.argv[1])


if __name__ == "__main__":
    main()
