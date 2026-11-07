-- ============================================================
-- Table: landing.yahoo_ttm_income_statement
-- Purpose: Store Yahoo Finance trailing twelve months
--          (TTM) income statement data.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_ttm_income_statement (
    ticker                                                     VARCHAR(10) NOT NULL,
    date                                                       DATE NOT NULL,

    -- Revenue and expenses
    total_revenue                                              BIGINT,
    operating_revenue                                          BIGINT,
    cost_of_revenue                                            BIGINT,
    gross_profit                                               BIGINT,
    operating_expense                                          BIGINT,
    total_expenses                                             BIGINT,
    research_and_development                                   BIGINT,
    selling_general_and_administration                         BIGINT,
    reconciled_cost_of_revenue                                 BIGINT,

    -- Operating profitability
    operating_income                                           BIGINT,
    total_operating_income_as_reported                         BIGINT,
    ebit                                                       BIGINT,
    ebitda                                                     BIGINT,
    normalized_ebitda                                          BIGINT,
    reconciled_depreciation                                    BIGINT,

    -- Income
    net_income                                                 BIGINT,
    net_income_common_stockholders                             BIGINT,
    net_income_including_noncontrolling_interests              BIGINT,
    net_income_continuous_operations                           BIGINT,
    net_income_from_continuing_operation_net_minority_interest BIGINT,
    net_income_from_continuing_and_discontinued_operation      BIGINT,
    diluted_ni_availto_com_stockholders                        BIGINT,
    normalized_income                                          BIGINT,

    -- Taxes
    pretax_income                                              BIGINT,
    tax_provision                                              BIGINT,
    tax_effect_of_unusual_items                                NUMERIC,
    tax_rate_for_calcs                                         NUMERIC,

    -- Non-operating income and expenses
    other_income_expense                                       BIGINT,
    other_non_operating_income_expenses                        BIGINT,

    -- Earnings per share
    basic_eps                                                  NUMERIC,
    diluted_eps                                                NUMERIC,

    -- Share counts
    basic_average_shares                                       BIGINT,
    diluted_average_shares                                     BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_ttm_income_statement
        PRIMARY KEY (ticker, date)
);

-- Queries by reporting period across multiple tickers.
CREATE INDEX IF NOT EXISTS idx_yahoo_ttm_income_statement_date
    ON landing.yahoo_ttm_income_statement (date DESC);

-- Monitoring recently ingested TTM statements.
CREATE INDEX IF NOT EXISTS idx_yahoo_ttm_income_statement_ingested_at
    ON landing.yahoo_ttm_income_statement (ingested_at DESC);