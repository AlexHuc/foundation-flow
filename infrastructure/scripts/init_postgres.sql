-- PostgreSQL Analytics Data Layer Schema
-- This schema stores ingestion from Yahoo Finance API

-- Create schema for landing data
CREATE SCHEMA IF NOT EXISTS landing;

-- Table for storing landing OHLC prices from Yahoo Finance
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
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_yahoo_prices_ticker_date UNIQUE (ticker, date)
);

-- Create indexes for landing prices table
CREATE INDEX IF NOT EXISTS idx_yahoo_prices_ticker 
    ON landing.yahoo_prices(ticker);
CREATE INDEX IF NOT EXISTS idx_yahoo_prices_ingested_at 
    ON landing.yahoo_prices(ingested_at DESC);

-- Table for storing landing fundamentals data
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
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_yahoo_fundamentals_ticker UNIQUE (ticker)
);

-- Create indexes for fundamentals table
CREATE INDEX IF NOT EXISTS idx_yahoo_fundamentals_ticker 
    ON landing.yahoo_fundamentals(ticker);
CREATE INDEX IF NOT EXISTS idx_yahoo_fundamentals_ingested_at 
    ON landing.yahoo_fundamentals(ingested_at DESC);

-- Table for storing pipeline run metadata
CREATE TABLE IF NOT EXISTS landing.pipeline_metadata (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20),
    status VARCHAR(50) NOT NULL, -- 'pending', 'running', 'success', 'failure'
    rows_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_pipeline_name_ticker_started_at UNIQUE (pipeline_name, ticker, started_at)
);

-- Create index for pipeline metadata
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_status 
    ON landing.pipeline_metadata(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_metadata_created_at 
    ON landing.pipeline_metadata(created_at DESC);

-- Grant permissions to airflow user
GRANT USAGE ON SCHEMA landing TO airflow;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA landing TO airflow;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA landing TO airflow;