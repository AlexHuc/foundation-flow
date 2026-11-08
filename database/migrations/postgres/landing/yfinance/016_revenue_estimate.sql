-- ============================================================
-- Table: landing.yahoo_revenue_estimate
-- Purpose: Store Yahoo Finance analyst revenue estimates.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_revenue_estimate (
    ticker             VARCHAR(10) NOT NULL,
    date               DATE NOT NULL,

    -- Relative estimate period:
    -- 0q  = current quarter
    -- +1q = next quarter
    -- 0y  = current fiscal year
    -- +1y = next fiscal year
    period             VARCHAR(10) NOT NULL,
    avg                BIGINT,
    low                BIGINT,
    high               BIGINT,
    number_of_analysts INTEGER,
    year_ago_revenue   BIGINT,
    growth             NUMERIC,
    currency           VARCHAR(10),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_revenue_estimate
        PRIMARY KEY (ticker, date, period)
);

-- Supports retrieving estimates across tickers by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_revenue_estimate_date
    ON landing.yahoo_revenue_estimate (date DESC);

-- Supports monitoring recently ingested revenue estimates.
CREATE INDEX IF NOT EXISTS idx_yahoo_revenue_estimate_ingested_at
    ON landing.yahoo_revenue_estimate (ingested_at DESC);