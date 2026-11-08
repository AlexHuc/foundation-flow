-- ============================================================
-- Table: landing.yahoo_eps_revisions
-- Purpose: Store Yahoo Finance analyst EPS estimate revisions.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_eps_revisions (
    ticker          VARCHAR(10) NOT NULL,
    date            DATE NOT NULL,

    -- Relative forecast period:
    -- 0q  = current quarter
    -- +1q = next quarter
    -- 0y  = current fiscal year
    -- +1y = next fiscal year
    period          VARCHAR(10) NOT NULL,
    up_last7days    INTEGER,
    up_last30days   INTEGER,
    down_last30days INTEGER,
    down_last7_days INTEGER,
    currency        VARCHAR(10),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_eps_revisions
        PRIMARY KEY (ticker, date, period)
);

-- Supports retrieving revisions across tickers by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_eps_revisions_date
    ON landing.yahoo_eps_revisions (date DESC);

-- Supports monitoring recently ingested EPS revisions.
CREATE INDEX IF NOT EXISTS idx_yahoo_eps_revisions_ingested_at
    ON landing.yahoo_eps_revisions (ingested_at DESC);