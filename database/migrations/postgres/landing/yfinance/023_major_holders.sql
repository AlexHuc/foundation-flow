-- ============================================================
-- Table: landing.yahoo_major_holders
-- Purpose: Store Yahoo Finance major holder ownership data.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_major_holders (
    ticker                          VARCHAR(10) NOT NULL,
    date                            DATE NOT NULL,
    insiders_percent_held           NUMERIC,
    institutions_percent_held       NUMERIC,
    institutions_float_percent_held NUMERIC,
    institutions_count              BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_major_holders
        PRIMARY KEY (ticker, date)
);

-- Supports retrieving ownership data by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_major_holders_date
    ON landing.yahoo_major_holders (date DESC);

-- Supports monitoring recently ingested ownership data.
CREATE INDEX IF NOT EXISTS idx_yahoo_major_holders_ingested_at
    ON landing.yahoo_major_holders (ingested_at DESC);