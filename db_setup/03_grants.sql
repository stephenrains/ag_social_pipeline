-- Grant the application role full access to the existing tables and sequences,
-- and make sure objects created later in this schema also auto-grant.
-- Run as a superuser inside the ag_social database:
--   psql -U postgres -d ag_social -f 03_grants.sql

GRANT USAGE ON SCHEMA public TO ag_social;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ag_social;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO ag_social;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ag_social;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO ag_social;
