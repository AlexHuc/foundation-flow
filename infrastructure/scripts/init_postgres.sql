-- PostgreSQL bootstrap
-- Database-level setup

CREATE SCHEMA IF NOT EXISTS landing;

-- Allow the ingestion role to use the landing schema.
GRANT USAGE, CREATE ON SCHEMA landing TO admin_pg;

-- Apply privileges to tables and sequences that already exist.
-- Future objects should also receive privileges through migrations
-- or explicit ALTER DEFAULT PRIVILEGES for the object-owning role.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA landing TO admin_pg;

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA landing TO admin_pg;