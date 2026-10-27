-- TimescaleDB bootstrap
-- Enable the extension and create the analytics schema.
-- Application tables and hypertables are managed by migrations.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE SCHEMA IF NOT EXISTS analytics;

-- The postgres role owns the database objects by default.
-- Grant runtime permissions explicitly if another role will access them.
GRANT USAGE, CREATE ON SCHEMA analytics TO admin_ts;