"""
Fetch Instagram account info for a username, download the profile picture
locally, and upsert into Postgres (ig_accounts).

Usage:
    python get_ig_account_data.py <username>
"""
import sys

from src.account_media import download_profile_pic
from src.db import get_engine, upsert_account
from src.ig_api import fetch_user_info
from src.transform_account import transform_user_info


def process_username(username: str) -> dict:
    """Run the account ingestion for one username. Returns a summary dict."""
    print(f"Fetching account info for @{username}...")
    payload = fetch_user_info(username)

    t = transform_user_info(payload)
    account = t["account"]
    profile_pic_url = t["profile_pic_url"]
    account_id = account["account_id"]

    profile_pic_local_path: str | None = None
    profile_pic_error: str | None = None
    if profile_pic_url:
        try:
            profile_pic_local_path = download_profile_pic(profile_pic_url, account_id)
            print(f"  profile pic saved: {profile_pic_local_path}")
        except Exception as e:
            profile_pic_error = str(e)
            print(f"  warning: profile pic download failed: {e}")
    else:
        profile_pic_error = "no profile_pic_url in payload"
        print(f"  warning: {profile_pic_error}")

    engine = get_engine()
    upsert_account(engine, account=account, profile_pic_local_path=profile_pic_local_path)

    summary = {
        "account_id": account_id,
        "username": account["username"],
        "followers": account["followers"],
        "following": account["following"],
        "published_posts": account["published_posts"],
        "profile_pic_local_path": profile_pic_local_path,
        "profile_pic_error": profile_pic_error,
    }
    print(f"\nDone. {summary}")
    return summary


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python get_ig_account_data.py <username>", file=sys.stderr)
        sys.exit(1)
    process_username(sys.argv[1])


if __name__ == "__main__":
    main()
