
-- Migration: 001_create_landing_tables.sql
-- Purpose: Create raw Yahoo Finance landing tables and pipeline metadata.
-- Database: PostgreSQL
-- Schema: landing

BEGIN;

CREATE SCHEMA IF NOT EXISTS landing;

-- Raw OHLCV prices from Yahoo Finance.
CREATE TABLE IF NOT EXISTS landing.yahoo_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    low NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    open NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    volume BIGINT NOT NULL,
    dividend NUMERIC,
    split NUMERIC,
    raw_response JSONB,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_yahoo_prices_ticker_date
        UNIQUE (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_yahoo_prices_ticker
    ON landing.yahoo_prices (ticker);

CREATE INDEX IF NOT EXISTS idx_yahoo_prices_ingested_at
    ON landing.yahoo_prices (ingested_at DESC);


-- Latest available fundamentals per ticker.
CREATE TABLE IF NOT EXISTS landing.yahoo_fundamentals (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    market_cap BIGINT,
    pe_ratio NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 4),
    earnings_per_share NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low NUMERIC(10, 2),
    average_volume BIGINT,
    beta NUMERIC(5, 3),
    raw_response JSONB,
    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_yahoo_fundamentals_ticker
        UNIQUE (ticker)
);

CREATE INDEX IF NOT EXISTS idx_yahoo_fundamentals_ticker
    ON landing.yahoo_fundamentals (ticker);

CREATE INDEX IF NOT EXISTS idx_yahoo_fundamentals_ingested_at
    ON landing.yahoo_fundamentals (ingested_at DESC);


-- Metadata for ingestion and transformation pipeline runs.
CREATE TABLE IF NOT EXISTS landing.pipeline_metadata (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20),
    status VARCHAR(50) NOT NULL,
    rows_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_pipeline_name_ticker_started_at
        UNIQUE (pipeline_name, ticker, started_at)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_status
    ON landing.pipeline_metadata (status);

CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_created_at
    ON landing.pipeline_metadata (created_at DESC);


-- Permissions for the Airflow/ingestion role.
GRANT USAGE ON SCHEMA landing TO admin_pg;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA landing TO admin_pg;

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA landing TO admin_pg;

COMMIT;