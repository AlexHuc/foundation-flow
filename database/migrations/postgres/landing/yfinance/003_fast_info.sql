-- ============================================================
-- Table: landing.yahoo_fast_info
-- Purpose: Store daily Yahoo Finance fast_info snapshots.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_fast_info (
    ticker                        VARCHAR(10) NOT NULL,
    date                          DATE NOT NULL,
    currency                      VARCHAR(10),

    -- Daily market prices.
    day_high                      NUMERIC,
    day_low                       NUMERIC,
    open                          NUMERIC,
    last_price                    NUMERIC,
    previous_close                NUMERIC,
    regular_market_previous_close NUMERIC,

    -- Stock exchange and instrument classification.
    exchange                      VARCHAR(20),
    quote_type                    VARCHAR(20),

    -- Moving-average prices.
    fifty_day_average             NUMERIC,
    two_hundred_day_average       NUMERIC,

    -- Trading volume and share information.
    last_volume                   BIGINT,
    ten_day_average_volume        BIGINT,
    three_month_average_volume    BIGINT,
    shares                        BIGINT,

    -- Market capitalization.
    market_cap                    BIGINT,

    -- Exchange timezone.
    timezone                      VARCHAR(50),

    -- Annual price performance and price range.
    year_change                   NUMERIC,
    year_high                     NUMERIC,
    year_low                      NUMERIC,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_fast_info
        PRIMARY KEY (ticker, date)
);

-- Efficiently retrieve recently ingested snapshots.
CREATE INDEX IF NOT EXISTS idx_yahoo_fast_info_ingested_at
    ON landing.yahoo_fast_info (ingested_at DESC);