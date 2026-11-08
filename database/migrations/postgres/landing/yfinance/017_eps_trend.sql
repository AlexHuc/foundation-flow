-- ============================================================
-- Table: landing.yahoo_eps_trend
-- Purpose: Store Yahoo Finance analyst EPS estimate trends.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_eps_trend (
    ticker       VARCHAR(10) NOT NULL,
    date         DATE NOT NULL,

    -- Relative forecast period:
    -- 0q  = current quarter
    -- +1q = next quarter
    -- 0y  = current fiscal year
    -- +1y = next fiscal year
    period       VARCHAR(10) NOT NULL,
    current      NUMERIC,
    "7days_ago"  NUMERIC,
    "30days_ago" NUMERIC,
    "60days_ago" NUMERIC,
    "90days_ago" NUMERIC,
    currency     VARCHAR(10),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_eps_trend
        PRIMARY KEY (ticker, date, period)
);

-- Supports querying EPS trends by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_eps_trend_date
    ON landing.yahoo_eps_trend (date DESC);

-- Supports monitoring recently ingested EPS trends.
CREATE INDEX IF NOT EXISTS idx_yahoo_eps_trend_ingested_at
    ON landing.yahoo_eps_trend (ingested_at DESC);