-- One-time migration: rename "local_path" columns to "key" since media now lives
-- in S3 and the column stores an S3 object key, not a filesystem path.
--
-- Existing column VALUES are unchanged by this rename. If you have legacy rows
-- with filesystem paths, run scripts/backfill_to_s3.py after this migration —
-- it detects path-shaped values and rewrites them to S3 keys.
--
-- Run as the owning role inside ag_social:
--   psql -U postgres -d ag_social -f 05_rename_local_paths_to_keys.sql

ALTER TABLE ig_post_media RENAME COLUMN local_path TO media_key;
ALTER TABLE ig_accounts   RENAME COLUMN profile_pic_local_path TO profile_pic_key;
