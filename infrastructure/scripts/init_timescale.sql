-- TimescaleDB Analytics Layer Schema
-- This schema stores time-series optimized data for analysis
-- Uses hypertables for efficient querying and compression

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create schema for landing
CREATE landing IF NOT EXISTS analytics;

-- Stock prices hypertable (time-series optimized)
CREATE TABLE IF NOT EXISTS landing.stock_prices (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Convert to hypertable if not already
SELECT create_hypertable('landing.stock_prices', 'time', 
    if_not_exists => TRUE, 
    migrate_data => TRUE);

-- Create indexes on hypertable
CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_time 
    ON landing.stock_prices (ticker, time DESC) 
    -- WHERE time > NOW() - INTERVAL '1 year';

-- !!!FIND SOLUTION FOR COMPRESSION POLICY!!!
-- ERROR:  functionality not supported under the current "apache" license. Learn more at https://tsdb.co/pdbir1r3
-- Enable compression on old data
-- COMPRESSION -> A feature in TimescaleDB that allows for efficient storage of historical data by reducing its size. It uses algorithms to compress data while maintaining query performance, making it ideal for time-series datasets where older data is accessed less frequently.
-- ALTER TABLE landing.stock_prices SET (
--     timescaledb.compress,
--     timescaledb.compress_orderby = 'time DESC',
--     timescaledb.compress_segmentby = 'ticker'
-- );

-- Add compression policy to automatically compress data older than 30 days
-- SELECT add_compression_policy('landing.stock_prices', INTERVAL '30 days',
--     if_not_exists => TRUE);

-- Stock returns (daily/weekly returns)
CREATE TABLE IF NOT EXISTS landing.stock_returns (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    daily_return NUMERIC(10, 6),
    weekly_return NUMERIC(10, 6),
    monthly_return NUMERIC(10, 6),
    annual_return NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('landing.stock_returns', 'time',
    if_not_exists => TRUE,
    migrate_data => TRUE);

CREATE INDEX IF NOT EXISTS idx_stock_returns_ticker_time
    ON landing.stock_returns (ticker, time DESC);

-- !!!FIND SOLUTION FOR COMPRESSION POLICY!!!
-- ERROR:  functionality not supported under the current "apache" license. Learn more at https://tsdb.co/pdbir1r3
-- ALTER TABLE landing.stock_returns SET (
--     timescaledb.compress,
--     timescaledb.compress_orderby = 'time DESC',
--     timescaledb.compress_segmentby = 'ticker'
-- );

-- SELECT add_compression_policy('landing.stock_returns', INTERVAL '30 days',
--     if_not_exists => TRUE);

-- Stock volatility metrics
CREATE TABLE IF NOT EXISTS landing.stock_volatility (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    volatility_20d NUMERIC(10, 6),
    volatility_60d NUMERIC(10, 6),
    volatility_252d NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('landing.stock_volatility', 'time',
    if_not_exists => TRUE,
    migrate_data => TRUE);

CREATE INDEX IF NOT EXISTS idx_stock_volatility_ticker_time
    ON landing.stock_volatility (ticker, time DESC);

ALTER TABLE landing.stock_volatility SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'ticker'
);

-- Moving averages
CREATE TABLE IF NOT EXISTS landing.moving_averages (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    ma_20 NUMERIC(10, 2),
    ma_50 NUMERIC(10, 2),
    ma_200 NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('landing.moving_averages', 'time',
    if_not_exists => TRUE,
    migrate_data => TRUE);

CREATE INDEX IF NOT EXISTS idx_moving_averages_ticker_time
    ON landing.moving_averages (ticker, time DESC);

-- ============================================================================
-- DIMENSION TABLES (Non-time-series)
-- ============================================================================

-- Stock metadata
CREATE TABLE IF NOT EXISTS landing.stock_metadata (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(100),
    currency VARCHAR(10),
    market_cap BIGINT,
    first_price_date DATE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_metadata_sector 
    ON landing.stock_metadata(sector);

-- Stock fundamentals (latest snapshot)
CREATE TABLE IF NOT EXISTS landing.stock_fundamentals (
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
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CONTINUOUS AGGREGATES (Optional pre-computed views)
-- ============================================================================

-- Daily OHLCV aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS landing.daily_ohlcv AS
SELECT
    time_bucket('1 day', time) as day,
    ticker,
    first(open) as open,
    max(high) as high,
    min(low) as low,
    last(close) as close,
    sum(volume) as volume
FROM landing.stock_prices
GROUP BY day, ticker
WITH DATA;

SELECT add_continuous_aggregate_policy('landing.daily_ohlcv',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT USAGE ON SCHEMA landing TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA landing TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA landing TO postgres;