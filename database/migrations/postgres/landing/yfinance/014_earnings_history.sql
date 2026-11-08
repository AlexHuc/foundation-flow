-- ============================================================
-- Table: landing.yahoo_earnings_history
-- Purpose: Store historical quarterly earnings results,
--          analyst EPS estimates, and earnings surprises.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_earnings_history (
    ticker           VARCHAR(10) NOT NULL,
    quarter          DATE NOT NULL,
    eps_actual       NUMERIC,
    eps_estimate     NUMERIC,
    eps_difference   NUMERIC,
    surprise_percent NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_earnings_history
        PRIMARY KEY (ticker, quarter)
);

-- Supports querying earnings history across tickers by quarter.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_history_quarter
    ON landing.yahoo_earnings_history (quarter DESC);

-- Supports monitoring recently ingested earnings records.
CREATE INDEX IF NOT EXISTS idx_yahoo_earnings_history_ingested_at
    ON landing.yahoo_earnings_history (ingested_at DESC);