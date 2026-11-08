-- ============================================================
-- Table: landing.yahoo_institutional_holders
-- Purpose: Store Yahoo Finance institutional ownership records.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_institutional_holders (
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

    CONSTRAINT pk_yahoo_institutional_holders
        PRIMARY KEY (
            ticker,
            date,
            date_reported,
            holder
        )
);

-- Supports retrieving snapshots across all tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_institutional_holders_date
    ON landing.yahoo_institutional_holders (date DESC);

-- Supports queries by institutional reporting date.
CREATE INDEX IF NOT EXISTS idx_yahoo_institutional_holders_date_reported
    ON landing.yahoo_institutional_holders (date_reported DESC);

-- Supports filtering ownership by institutional investor.
CREATE INDEX IF NOT EXISTS idx_yahoo_institutional_holders_holder
    ON landing.yahoo_institutional_holders (holder);

-- Supports monitoring recent ingestion activity.
CREATE INDEX IF NOT EXISTS idx_yahoo_institutional_holders_ingested_at
    ON landing.yahoo_institutional_holders (ingested_at DESC);