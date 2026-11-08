-- ============================================================
-- Table: landing.yahoo_insider_purchases
-- Purpose: Store Yahoo Finance six-month insider activity
--          summary metrics.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_insider_purchases (
    ticker                    VARCHAR(10) NOT NULL,
    date                      DATE NOT NULL,
    insider_purchases_last_6m VARCHAR(100) NOT NULL,
    shares                    NUMERIC,
    trans                     BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_insider_purchases
        PRIMARY KEY (
            ticker,
            date,
            insider_purchases_last_6m
        )
);

-- Supports retrieving insider activity snapshots by date.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_purchases_date
    ON landing.yahoo_insider_purchases (date DESC);

-- Supports monitoring recently ingested records.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_purchases_ingested_at
    ON landing.yahoo_insider_purchases (ingested_at DESC);