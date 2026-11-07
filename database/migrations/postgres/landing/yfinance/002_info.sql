-- ============================================================
-- Table: landing.yahoo_info
-- Purpose: Store Yahoo Finance company fundamentals.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_info (
    ticker              VARCHAR(10) NOT NULL,
    date                DATE NOT NULL,
    market_cap          BIGINT,
    pe_ratio            NUMERIC(10, 2),
    dividend_yield      NUMERIC(10, 4),
    earnings_per_share  NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low  NUMERIC(10, 2),
    average_volume      BIGINT,
    beta                NUMERIC(5, 3),
    raw_response        JSONB,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_info
        PRIMARY KEY (ticker, date)
);

-- Supports monitoring recent ingestion activity.
CREATE INDEX IF NOT EXISTS idx_yahoo_info_ingested_at
    ON landing.yahoo_info (ingested_at DESC);