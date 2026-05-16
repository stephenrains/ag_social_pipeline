from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import DB_URL


def get_engine() -> Engine:
    return create_engine(DB_URL, future=True)


def upsert_post(engine: Engine, post: dict, media: list[dict], users_tagged: list[str], coauthors: list[str]) -> None:
    """
    Upsert a post and replace its child rows (media, tags, coauthors) atomically.

    `post` keys: ig_post_id, post_owner_username, caption, post_type, likes, views,
                 comments, paid_partnership, taken_at
    `media` items: position, media_type, local_path, height, width
    """
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ig_posts (
                    ig_post_id, post_owner_username, caption, post_type,
                    likes, views, comments, paid_partnership, taken_at,
                    fetched_at, updated_at
                )
                VALUES (
                    :ig_post_id, :post_owner_username, :caption, :post_type,
                    :likes, :views, :comments, :paid_partnership, :taken_at,
                    :now, :now
                )
                ON CONFLICT (ig_post_id) DO UPDATE SET
                    post_owner_username = EXCLUDED.post_owner_username,
                    caption             = EXCLUDED.caption,
                    post_type           = EXCLUDED.post_type,
                    likes               = EXCLUDED.likes,
                    views               = EXCLUDED.views,
                    comments            = EXCLUDED.comments,
                    paid_partnership    = EXCLUDED.paid_partnership,
                    taken_at            = EXCLUDED.taken_at,
                    updated_at          = EXCLUDED.updated_at
                """
            ),
            {**post, "now": now},
        )

        post_id = post["ig_post_id"]

        conn.execute(text("DELETE FROM ig_post_media WHERE ig_post_id = :pid"), {"pid": post_id})
        conn.execute(text("DELETE FROM ig_post_users_tagged WHERE ig_post_id = :pid"), {"pid": post_id})
        conn.execute(text("DELETE FROM ig_post_coauthors WHERE ig_post_id = :pid"), {"pid": post_id})

        if media:
            conn.execute(
                text(
                    """
                    INSERT INTO ig_post_media (ig_post_id, position, media_type, local_path, height, width)
                    VALUES (:ig_post_id, :position, :media_type, :local_path, :height, :width)
                    """
                ),
                [{"ig_post_id": post_id, **m} for m in media],
            )

        if users_tagged:
            conn.execute(
                text("INSERT INTO ig_post_users_tagged (ig_post_id, username) VALUES (:pid, :u)"),
                [{"pid": post_id, "u": u} for u in users_tagged],
            )

        if coauthors:
            conn.execute(
                text("INSERT INTO ig_post_coauthors (ig_post_id, username) VALUES (:pid, :u)"),
                [{"pid": post_id, "u": u} for u in coauthors],
            )


def upsert_account(engine: Engine, account: dict, profile_pic_local_path: str | None) -> None:
    """
    Upsert one row into ig_accounts. Conflict key is (account_type, account_id).
    `account` must contain all ig_accounts fields except profile_pic_local_path,
    fetched_at, and updated_at.
    """
    now = datetime.now(timezone.utc)
    params = {**account, "profile_pic_local_path": profile_pic_local_path, "now": now}

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ig_accounts (
                    account_type, account_id, profile_type, is_private, username,
                    full_name, profile_pic_local_path, followers, following,
                    published_posts, contact_method, city, bio,
                    bio_link_type, bio_link_title, fetched_at, updated_at
                )
                VALUES (
                    :account_type, :account_id, :profile_type, :is_private, :username,
                    :full_name, :profile_pic_local_path, :followers, :following,
                    :published_posts, :contact_method, :city, :bio,
                    :bio_link_type, :bio_link_title, :now, :now
                )
                ON CONFLICT (account_type, account_id) DO UPDATE SET
                    profile_type           = EXCLUDED.profile_type,
                    is_private             = EXCLUDED.is_private,
                    username               = EXCLUDED.username,
                    full_name              = EXCLUDED.full_name,
                    profile_pic_local_path = COALESCE(EXCLUDED.profile_pic_local_path, ig_accounts.profile_pic_local_path),
                    followers              = EXCLUDED.followers,
                    following              = EXCLUDED.following,
                    published_posts        = EXCLUDED.published_posts,
                    contact_method         = EXCLUDED.contact_method,
                    city                   = EXCLUDED.city,
                    bio                    = EXCLUDED.bio,
                    bio_link_type          = EXCLUDED.bio_link_type,
                    bio_link_title         = EXCLUDED.bio_link_title,
                    updated_at             = EXCLUDED.updated_at
                """
            ),
            params,
        )
