-- Run inside the ag_social database:
--   psql -U postgres -d ag_social -f 04_create_accounts_table.sql

CREATE TABLE IF NOT EXISTS ig_accounts (
    account_type            TEXT        NOT NULL,            -- 'instagram' for now
    account_id              TEXT        NOT NULL,            -- IG user id, e.g. "3860610513"
    profile_type            SMALLINT,
    is_private              BOOLEAN     NOT NULL,
    username                TEXT        NOT NULL,
    full_name               TEXT,
    profile_pic_key         TEXT,                            -- S3 object key, e.g. account_profile_images/{account_id}.jpg
    followers               INTEGER,
    following               INTEGER,
    published_posts         INTEGER,
    contact_method          TEXT,
    city                    TEXT,
    bio                     TEXT,
    bio_link_type           TEXT,
    bio_link_title          TEXT,
    fetched_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (account_type, account_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ig_accounts_type_username_idx
    ON ig_accounts (account_type, username);
