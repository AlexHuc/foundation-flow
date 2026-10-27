
-- Migration: 001_create_analytics_tables.sql
-- Purpose: Create time-series analytics tables and supporting objects.
-- Database: TimescaleDB
-- Schema: analytics

BEGIN;

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE SCHEMA IF NOT EXISTS analytics;


-- ---------------------------------------------------------------------------
-- STOCK PRICES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.stock_prices (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable(
    'analytics.stock_prices',
    'time',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_time
    ON analytics.stock_prices (ticker, time DESC);


-- ---------------------------------------------------------------------------
-- STOCK RETURNS
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.stock_returns (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    daily_return NUMERIC(10, 6),
    weekly_return NUMERIC(10, 6),
    monthly_return NUMERIC(10, 6),
    annual_return NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable(
    'analytics.stock_returns',
    'time',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_stock_returns_ticker_time
    ON analytics.stock_returns (ticker, time DESC);


-- ---------------------------------------------------------------------------
-- STOCK VOLATILITY
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.stock_volatility (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    volatility_20d NUMERIC(10, 6),
    volatility_60d NUMERIC(10, 6),
    volatility_252d NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable(
    'analytics.stock_volatility',
    'time',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_stock_volatility_ticker_time
    ON analytics.stock_volatility (ticker, time DESC);


-- ---------------------------------------------------------------------------
-- MOVING AVERAGES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.moving_averages (
    time TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    ma_20 NUMERIC(10, 2),
    ma_50 NUMERIC(10, 2),
    ma_200 NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable(
    'analytics.moving_averages',
    'time',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_moving_averages_ticker_time
    ON analytics.moving_averages (ticker, time DESC);


-- ---------------------------------------------------------------------------
-- DIMENSION TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.stock_metadata (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(100),
    currency VARCHAR(10),
    market_cap BIGINT,
    first_price_date DATE,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_metadata_sector
    ON analytics.stock_metadata (sector);


CREATE TABLE IF NOT EXISTS analytics.stock_fundamentals (
    ticker VARCHAR(20) PRIMARY KEY,
    pe_ratio NUMERIC(10, 2),
    earnings_per_share NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 4),
    book_value NUMERIC(15, 2),
    price_to_book NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low NUMERIC(10, 2),
    average_volume BIGINT,
    beta NUMERIC(5, 3),
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- ---------------------------------------------------------------------------
-- DAILY OHLCV CONTINUOUS AGGREGATE
-- ---------------------------------------------------------------------------

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_ohlcv
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 day', time) AS day,
    ticker,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM analytics.stock_prices
GROUP BY time_bucket(INTERVAL '1 day', time), ticker
WITH DATA;

-- Refresh recent data regularly.
SELECT add_continuous_aggregate_policy(
    'analytics.daily_ohlcv',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

COMMIT;
