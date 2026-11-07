-- ============================================================
-- Table: landing.yahoo_history
-- Purpose: Store daily historical OHLCV stock market data.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_history (
    ticker    VARCHAR(10) NOT NULL,
    date      DATE NOT NULL,
    open      NUMERIC NOT NULL,
    high      NUMERIC NOT NULL,
    low       NUMERIC NOT NULL,
    close     NUMERIC NOT NULL,
    adj_close NUMERIC NOT NULL,
    volume    BIGINT NOT NULL,
    dividend  NUMERIC,
    split     NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_history
        PRIMARY KEY (ticker, date)
);

-- Supports monitoring recent historical-price ingestions.
CREATE INDEX IF NOT EXISTS idx_yahoo_history_ingested_at
    ON landing.yahoo_history (ingested_at DESC);