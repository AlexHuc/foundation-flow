-- ============================================================
-- Table: landing.yahoo_insider_transactions
-- Purpose: Store Yahoo Finance insider transaction records.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_insider_transactions (
    ticker         VARCHAR(10) NOT NULL,
    date           DATE NOT NULL,
    transaction_id VARCHAR(64) NOT NULL,
    shares         BIGINT,
    value          NUMERIC,
    url            TEXT,
    text           TEXT,
    insider        TEXT,
    position       TEXT,
    transaction    TEXT,
    start_date     DATE,
    ownership      VARCHAR(20),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_insider_transactions
        PRIMARY KEY (ticker, date, transaction_id)
);

-- Supports querying snapshots across tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_transactions_date
    ON landing.yahoo_insider_transactions (date DESC);

-- Supports retrieving transactions by reported date.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_transactions_start_date
    ON landing.yahoo_insider_transactions (start_date DESC);

-- Supports filtering transactions by insider.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_transactions_insider
    ON landing.yahoo_insider_transactions (insider);

-- Supports monitoring ingestion activity.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_transactions_ingested_at
    ON landing.yahoo_insider_transactions (ingested_at DESC);