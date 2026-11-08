-- ============================================================
-- Table: landing.yahoo_growth_estimates
-- Purpose: Store Yahoo Finance stock and index growth estimates.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_growth_estimates (
    ticker      VARCHAR(10) NOT NULL,
    date        DATE NOT NULL,

    -- Relative forecast period:
    -- 0q  = current quarter
    -- +1q = next quarter
    -- 0y  = current fiscal year
    -- +1y = next fiscal year
    -- LTG = long-term growth
    period      VARCHAR(10) NOT NULL,
    stock_trend NUMERIC,
    index_trend NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_growth_estimates
        PRIMARY KEY (ticker, date, period)
);

-- Supports retrieving growth estimates by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_growth_estimates_date
    ON landing.yahoo_growth_estimates (date DESC);

-- Supports monitoring recently ingested growth estimates.
CREATE INDEX IF NOT EXISTS idx_yahoo_growth_estimates_ingested_at
    ON landing.yahoo_growth_estimates (ingested_at DESC);