-- ============================================================
-- Table: landing.yahoo_calendar
-- Purpose: Store Yahoo Finance financial calendar information.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_calendar (
    ticker           VARCHAR(10) NOT NULL,
    date             DATE NOT NULL,
    dividend_date    DATE,
    ex_dividend_date DATE,
    earnings_dates   DATE[],
    earnings_high    NUMERIC,
    earnings_low     NUMERIC,
    earnings_average NUMERIC,
    revenue_high     BIGINT,
    revenue_low      BIGINT,
    revenue_average  BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_calendar
        PRIMARY KEY (ticker, date)
);

-- Supports retrieving calendar snapshots by date.
CREATE INDEX IF NOT EXISTS idx_yahoo_calendar_date
    ON landing.yahoo_calendar (date DESC);

-- Supports monitoring recently ingested calendar records.
CREATE INDEX IF NOT EXISTS idx_yahoo_calendar_ingested_at
    ON landing.yahoo_calendar (ingested_at DESC);