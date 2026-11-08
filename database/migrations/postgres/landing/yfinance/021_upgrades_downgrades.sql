-- ============================================================
-- Table: landing.yahoo_upgrades_downgrades
-- Purpose: Store historical analyst rating changes and
--          stock price target revisions from Yahoo Finance.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_upgrades_downgrades (
    ticker               VARCHAR(10) NOT NULL,
    grade_date           TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    firm                 TEXT NOT NULL,
    to_grade             TEXT,
    from_grade           TEXT,
    action               VARCHAR(30),
    price_target_action  VARCHAR(30),
    current_price_target NUMERIC,
    prior_price_target   NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_upgrades_downgrades
        PRIMARY KEY (ticker, grade_date, firm)
);

-- Supports finding recent analyst events across tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_upgrades_downgrades_grade_date
    ON landing.yahoo_upgrades_downgrades (grade_date DESC);

-- Supports filtering events by analyst firm.
CREATE INDEX IF NOT EXISTS idx_yahoo_upgrades_downgrades_firm
    ON landing.yahoo_upgrades_downgrades (firm);

-- Supports monitoring recently ingested analyst events.
CREATE INDEX IF NOT EXISTS idx_yahoo_upgrades_downgrades_ingested_at
    ON landing.yahoo_upgrades_downgrades (ingested_at DESC);