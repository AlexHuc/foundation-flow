-- ============================================================
-- Table: landing.yahoo_recommendations
-- Purpose: Store Yahoo Finance analyst recommendation counts.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_recommendations (
    ticker      VARCHAR(10) NOT NULL,
    date        DATE NOT NULL,

    -- Relative recommendation period:
    -- 0m  = current month
    -- -1m = previous month
    -- -2m = two months ago
    -- -3m = three months ago
    period      VARCHAR(10) NOT NULL,
    strong_buy  INTEGER,
    buy         INTEGER,
    hold        INTEGER,
    sell        INTEGER,
    strong_sell INTEGER,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_recommendations
        PRIMARY KEY (ticker, date, period)
);

-- Supports retrieving recommendations by snapshot date.
CREATE INDEX IF NOT EXISTS idx_yahoo_recommendations_date
    ON landing.yahoo_recommendations (date DESC);

-- Supports monitoring recently ingested recommendations.
CREATE INDEX IF NOT EXISTS idx_yahoo_recommendations_ingested_at
    ON landing.yahoo_recommendations (ingested_at DESC);