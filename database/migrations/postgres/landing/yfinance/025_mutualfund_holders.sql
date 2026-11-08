-- ============================================================
-- Table: landing.yahoo_mutualfund_holders
-- Purpose: Store Yahoo Finance mutual fund ownership records.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_mutualfund_holders (
    ticker        VARCHAR(10) NOT NULL,
    date          DATE NOT NULL,
    date_reported DATE NOT NULL,
    holder        TEXT NOT NULL,
    pct_held      NUMERIC,
    shares        BIGINT,
    value         BIGINT,
    pct_change    NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_mutualfund_holders
        PRIMARY KEY (
            ticker,
            date,
            date_reported,
            holder
        )
);

-- Supports retrieving snapshots across all tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_mutualfund_holders_date
    ON landing.yahoo_mutualfund_holders (date DESC);

-- Supports queries by holdings reporting date.
CREATE INDEX IF NOT EXISTS idx_yahoo_mutualfund_holders_date_reported
    ON landing.yahoo_mutualfund_holders (date_reported DESC);

-- Supports filtering by mutual fund or ETF name.
CREATE INDEX IF NOT EXISTS idx_yahoo_mutualfund_holders_holder
    ON landing.yahoo_mutualfund_holders (holder);

-- Supports monitoring recently ingested records.
CREATE INDEX IF NOT EXISTS idx_yahoo_mutualfund_holders_ingested_at
    ON landing.yahoo_mutualfund_holders (ingested_at DESC);