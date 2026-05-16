"""
One-shot backfill: rewrite `media_key` / `profile_pic_key` rows that still hold a
local filesystem path so they point at the equivalent S3 key.

This does NOT touch S3 — it assumes media has already been uploaded there.
Run AFTER applying db_setup/05_rename_local_paths_to_keys.sql.
Safe to re-run — rows that already look like S3 keys are skipped.

Usage:
    python -m scripts.backfill_to_s3            # rewrite paths
    python -m scripts.backfill_to_s3 --dry-run  # show what would change
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from src.config import MEDIA_ROOT
from src.db import get_engine


def _looks_like_local_path(value: str | None) -> bool:
    return bool(value) and value.startswith("/")


def _key_for_post_media(local_path: str) -> str | None:
    """
    /Users/.../ag_social_media_saves/fourtillfourcafe/3896.../0.jpg
      -> posts/fourtillfourcafe/3896.../0.jpg
    """
    if not MEDIA_ROOT:
        return None
    try:
        rel = Path(local_path).resolve().relative_to(Path(MEDIA_ROOT).resolve())
    except ValueError:
        return None
    return f"posts/{rel.as_posix()}"


def _key_for_profile_pic(local_path: str) -> str | None:
    """
    /Users/.../ag_social_media_saves/account_profile_images/{account_id}.jpg
      -> account_profile_images/{account_id}.jpg
    """
    if not MEDIA_ROOT:
        return None
    try:
        rel = Path(local_path).resolve().relative_to(Path(MEDIA_ROOT).resolve())
    except ValueError:
        return None
    return rel.as_posix()


def rewrite_post_media(engine, dry_run: bool) -> tuple[int, int, int]:
    rewritten = skipped = errors = 0
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, media_key FROM ig_post_media")).all()

    for row_id, media_key in rows:
        if not _looks_like_local_path(media_key):
            skipped += 1
            continue
        s3_key = _key_for_post_media(media_key)
        if not s3_key:
            print(f"  [media id={row_id}] not under MEDIA_ROOT: {media_key}")
            errors += 1
            continue
        if dry_run:
            print(f"  [dry] media id={row_id}: {media_key} -> {s3_key}")
            rewritten += 1
            continue
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE ig_post_media SET media_key = :k WHERE id = :id"),
                {"k": s3_key, "id": row_id},
            )
        print(f"  media id={row_id}: -> {s3_key}")
        rewritten += 1
    return rewritten, skipped, errors


def rewrite_profile_pics(engine, dry_run: bool) -> tuple[int, int, int]:
    rewritten = skipped = errors = 0
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT account_type, account_id, profile_pic_key FROM ig_accounts")
        ).all()

    for account_type, account_id, key in rows:
        if not _looks_like_local_path(key):
            skipped += 1
            continue
        s3_key = _key_for_profile_pic(key)
        if not s3_key:
            print(f"  [account {account_type}/{account_id}] not under MEDIA_ROOT: {key}")
            errors += 1
            continue
        if dry_run:
            print(f"  [dry] account {account_id}: {key} -> {s3_key}")
            rewritten += 1
            continue
        with engine.begin() as conn:
            conn.execute(
                text(
                    """UPDATE ig_accounts SET profile_pic_key = :k
                       WHERE account_type = :t AND account_id = :id"""
                ),
                {"k": s3_key, "t": account_type, "id": account_id},
            )
        print(f"  account {account_id}: -> {s3_key}")
        rewritten += 1
    return rewritten, skipped, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="don't update DB")
    args = parser.parse_args()

    if not MEDIA_ROOT:
        print("MEDIA_ROOT is not set in .env; can't derive S3 keys from local paths.", file=sys.stderr)
        sys.exit(1)

    engine = get_engine()

    print("Rewriting post media keys...")
    r1, s1, e1 = rewrite_post_media(engine, args.dry_run)
    print(f"  rewritten={r1}, already_s3={s1}, errors={e1}")

    print("\nRewriting profile pic keys...")
    r2, s2, e2 = rewrite_profile_pics(engine, args.dry_run)
    print(f"  rewritten={r2}, already_s3={s2}, errors={e2}")

    print(f"\nTotal: rewritten={r1 + r2}, already_s3={s1 + s2}, errors={e1 + e2}")


if __name__ == "__main__":
    main()
