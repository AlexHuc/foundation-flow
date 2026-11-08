-- ============================================================
-- Table: landing.yahoo_earnings_estimate
-- Purpose: Store Yahoo Finance analyst earnings estimates.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_earnings_estimate (
    ticker             VARCHAR(10) NOT NULL,
    date               DATE NOT NULL,

    -- Relative estimate period:
    -- 0q  = current quarter
    -- +1q = next quarter
    -- 0y  = current fiscal year
    -- +1y = next fiscal year
    period VARCHAR(10) NOT NULL,
    avg                NUMERIC,
    low                NUMERIC,
    high               NUMERIC,
    year_ago_eps       NUMERIC,
    number_of_analysts INTEGER,
    growth             NUMERIC,
    currency           VARCHAR(10),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_earnings_estimate
        PRIMARY KEY (ticker, date, period)
);

-- Supports retrieving estimates across tickers by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_estimate_date
    ON landing.yahoo_earnings_estimate (date DESC);

-- Supports monitoring recently ingested earnings estimates.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_estimate_ingested_at
    ON landing.yahoo_earnings_estimate (ingested_at DESC);