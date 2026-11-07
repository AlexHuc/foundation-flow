-- Permissions for the Airflow/ingestion role.
GRANT USAGE ON SCHEMA landing TO admin_pg;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA landing TO admin_pg;

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA landing TO admin_pg;