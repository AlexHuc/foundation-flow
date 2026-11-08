-- ============================================================
-- Table: landing.yahoo_insider_roster_holders
-- Purpose: Store Yahoo Finance insider roster and
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_insider_roster_holders (
    ticker                  VARCHAR(10) NOT NULL,
    date                    DATE NOT NULL,
    name                    TEXT NOT NULL,
    position                TEXT,
    url                     TEXT,
    most_recent_transaction TEXT,
    latest_transaction_date DATE,
    shares_owned_directly   BIGINT,
    position_direct_date    DATE,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_insider_roster_holders
        PRIMARY KEY (ticker, date, name)
);

-- Supports retrieving snapshots by date.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_roster_holders_date
    ON landing.yahoo_insider_roster_holders (date DESC);

-- Supports querying historical records by insider.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_roster_holders_name
    ON landing.yahoo_insider_roster_holders (name);

-- Supports retrieving recent insider transactions.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_roster_holders_transaction_date
    ON landing.yahoo_insider_roster_holders (
        latest_transaction_date DESC
    );

-- Supports monitoring ingestion activity.
CREATE INDEX IF NOT EXISTS idx_yahoo_insider_roster_holders_ingested_at
    ON landing.yahoo_insider_roster_holders (ingested_at DESC);