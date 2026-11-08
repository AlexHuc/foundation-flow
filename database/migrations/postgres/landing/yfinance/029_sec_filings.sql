-- ============================================================
-- Table: landing.yahoo_sec_filings
-- Purpose: Store SEC filing metadata from Yahoo Finance.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_sec_filings (
    ticker      VARCHAR(10) NOT NULL,
    date        DATE NOT NULL,
    edgar_url   TEXT NOT NULL,
    filing_date DATE NOT NULL,
    epoch_date  BIGINT,
    type        VARCHAR(30),
    title       TEXT,
    exhibits    JSONB,
    max_age     INTEGER,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_sec_filings
        PRIMARY KEY (ticker, date, edgar_url)
);

CREATE INDEX IF NOT EXISTS idx_yahoo_sec_filings_date
    ON landing.yahoo_sec_filings (date DESC);

CREATE INDEX IF NOT EXISTS idx_yahoo_sec_filings_filing_date
    ON landing.yahoo_sec_filings (filing_date DESC);

CREATE INDEX IF NOT EXISTS idx_yahoo_sec_filings_type
    ON landing.yahoo_sec_filings (type);

CREATE INDEX IF NOT EXISTS idx_yahoo_sec_filings_ingested_at
    ON landing.yahoo_sec_filings (ingested_at DESC);