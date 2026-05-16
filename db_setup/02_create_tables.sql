-- Run inside the ag_social database: `psql -U postgres -d ag_social -f 02_create_tables.sql`

CREATE TABLE IF NOT EXISTS ig_posts (
    ig_post_id          TEXT PRIMARY KEY,
    post_owner_username TEXT        NOT NULL,
    caption             TEXT,
    post_type           SMALLINT    NOT NULL,           -- 1=photo, 2=video/reel, 8=carousel
    likes               INTEGER     NOT NULL,           -- -1 when disabled/unknown
    views               INTEGER     NOT NULL,           -- -1 when disabled/unknown
    comments            INTEGER     NOT NULL,           -- -1 when disabled/unknown
    paid_partnership    BOOLEAN     NOT NULL,
    taken_at            TIMESTAMPTZ,
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ig_posts_owner_idx ON ig_posts (post_owner_username);

CREATE TABLE IF NOT EXISTS ig_post_media (
    id          BIGSERIAL PRIMARY KEY,
    ig_post_id  TEXT     NOT NULL REFERENCES ig_posts(ig_post_id) ON DELETE CASCADE,
    position    SMALLINT NOT NULL,                       -- 0 for single, 0..n for carousel
    media_type  SMALLINT NOT NULL,                       -- 1=photo, 2=video
    media_key   TEXT     NOT NULL,                       -- S3 object key, e.g. posts/{username}/{post_id}/{position}.{ext}
    height      INTEGER  NOT NULL,
    width       INTEGER  NOT NULL,
    UNIQUE (ig_post_id, position)
);

CREATE TABLE IF NOT EXISTS ig_post_users_tagged (
    ig_post_id TEXT NOT NULL REFERENCES ig_posts(ig_post_id) ON DELETE CASCADE,
    username   TEXT NOT NULL,
    PRIMARY KEY (ig_post_id, username)
);

CREATE TABLE IF NOT EXISTS ig_post_coauthors (
    ig_post_id TEXT NOT NULL REFERENCES ig_posts(ig_post_id) ON DELETE CASCADE,
    username   TEXT NOT NULL,
    PRIMARY KEY (ig_post_id, username)
);
