-- ============================================================
-- Table: landing.yahoo_earnings_dates
-- Purpose: Store historical and upcoming earnings announcements,
--          EPS estimates, reported EPS, and earnings surprises.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_earnings_dates (
    ticker           VARCHAR(10) NOT NULL,
    earnings_date    TIMESTAMPTZ NOT NULL,
    eps_estimate     NUMERIC,
    reported_eps     NUMERIC,
    surprise_percent NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_earnings_dates
        PRIMARY KEY (ticker, earnings_date)
);

-- Supports finding earnings announcements across all tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_dates_date
    ON landing.yahoo_earnings_dates (earnings_date DESC);

-- Supports monitoring recently ingested earnings records.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_dates_ingested_at
    ON landing.yahoo_earnings_dates (ingested_at DESC);