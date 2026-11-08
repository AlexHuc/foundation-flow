-- ============================================================
-- Table: landing.yahoo_option_chain
-- Purpose: Store Yahoo Finance call and put option chains.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_option_chain (
    ticker             VARCHAR(10) NOT NULL,
    date               DATE NOT NULL,
    contract_symbol    VARCHAR(100) NOT NULL,
    expiration         DATE NOT NULL,
    option_type        VARCHAR(4) NOT NULL,
    last_trade_date    TIMESTAMPTZ,
    strike             NUMERIC,
    last_price         NUMERIC,
    bid                NUMERIC,
    ask                NUMERIC,
    change             NUMERIC,
    percent_change     NUMERIC,
    volume             BIGINT,
    open_interest      BIGINT,
    implied_volatility NUMERIC,
    in_the_money       BOOLEAN,
    contract_size      VARCHAR(30),
    currency           VARCHAR(10),

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_option_chain
        PRIMARY KEY (ticker, date, contract_symbol),

    CONSTRAINT chk_yahoo_option_chain_type
        CHECK (option_type IN ('CALL', 'PUT'))
);

-- Supports retrieving options by expiration.
CREATE INDEX IF NOT EXISTS idx_yahoo_option_chain_expiration
    ON landing.yahoo_option_chain (expiration);

-- Supports filtering by expiration and option type.
CREATE INDEX IF NOT EXISTS idx_yahoo_option_chain_expiration_type
    ON landing.yahoo_option_chain (
        ticker,
        expiration,
        option_type
    );

-- Supports querying the latest snapshots across tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_option_chain_date
    ON landing.yahoo_option_chain (date DESC);

-- Supports querying options by strike.
CREATE INDEX IF NOT EXISTS idx_yahoo_option_chain_strike
    ON landing.yahoo_option_chain (ticker, expiration, strike);

-- Supports monitoring recently ingested option contracts.
CREATE INDEX IF NOT EXISTS idx_yahoo_option_chain_ingested_at
    ON landing.yahoo_option_chain (ingested_at DESC);