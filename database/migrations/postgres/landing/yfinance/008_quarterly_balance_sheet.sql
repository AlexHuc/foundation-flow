-- ============================================================
-- Table: landing.yahoo_quarterly_balance_sheet
-- Purpose: Store Yahoo Finance quarterly balance sheet data.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_quarterly_balance_sheet (
    ticker                                                   VARCHAR(10) NOT NULL,
    date                                                     DATE NOT NULL,

    -- Shares and capital structure
    ordinary_shares_number                                   BIGINT,
    share_issued                                             BIGINT,
    total_debt                                               BIGINT,
    tangible_book_value                                      BIGINT,
    invested_capital                                         BIGINT,
    working_capital                                          BIGINT,
    net_tangible_assets                                      BIGINT,
    capital_lease_obligations                                BIGINT,
    common_stock_equity                                      BIGINT,
    total_capitalization                                     BIGINT,

    -- Shareholders' equity
    total_equity_gross_minority_interest                     BIGINT,
    stockholders_equity                                      BIGINT,
    gains_losses_not_affecting_retained_earnings             BIGINT,
    other_equity_adjustments                                 BIGINT,
    retained_earnings                                        BIGINT,
    additional_paid_in_capital                               BIGINT,
    capital_stock                                            BIGINT,
    common_stock                                             BIGINT,

    -- Non-current liabilities
    total_liabilities_net_minority_interest                  BIGINT,
    total_non_current_liabilities_net_minority_interest      BIGINT,
    other_non_current_liabilities                            BIGINT,
    tradeand_other_payables_non_current                      BIGINT,
    non_current_deferred_liabilities                         BIGINT,
    non_current_deferred_taxes_liabilities                   BIGINT,
    long_term_debt_and_capital_lease_obligation              BIGINT,
    long_term_capital_lease_obligation                       BIGINT,

    -- Current liabilities
    current_liabilities                                      BIGINT,
    other_current_liabilities                                BIGINT,
    current_debt_and_capital_lease_obligation                BIGINT,
    current_capital_lease_obligation                         BIGINT,
    pensionand_other_post_retirement_benefit_plans_current   BIGINT,
    payables_and_accrued_expenses                            BIGINT,
    current_accrued_expenses                                 BIGINT,
    payables                                                 BIGINT,
    other_payable                                            BIGINT,
    accounts_payable                                         BIGINT,

    -- Total and non-current assets
    total_assets                                             BIGINT,
    total_non_current_assets                                 BIGINT,
    other_non_current_assets                                 BIGINT,
    non_current_prepaid_assets                               BIGINT,

    -- Goodwill and intangible assets
    goodwill_and_other_intangible_assets                     BIGINT,
    other_intangible_assets                                  BIGINT,
    goodwill                                                 BIGINT,

    -- Property, plant and equipment
    net_ppe                                                  BIGINT,
    accumulated_depreciation                                 BIGINT,
    gross_ppe                                                BIGINT,
    leases                                                   BIGINT,
    construction_in_progress                                 BIGINT,
    other_properties                                         BIGINT,
    machinery_furniture_equipment                            BIGINT,
    properties                                               BIGINT,

    -- Current assets and inventory
    current_assets                                           BIGINT,
    other_current_assets                                     BIGINT,
    prepaid_assets                                           BIGINT,
    inventory                                                BIGINT,
    finished_goods                                           BIGINT,
    work_in_process                                          BIGINT,
    raw_materials                                            BIGINT,

    -- Receivables
    receivables                                              BIGINT,
    accounts_receivable                                      BIGINT,

    -- Cash and investments
    cash_cash_equivalents_and_short_term_investments         BIGINT,
    other_short_term_investments                             BIGINT,
    cash_and_cash_equivalents                                BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_quarterly_balance_sheet
        PRIMARY KEY (ticker, date)
);

-- Supports queries across tickers by fiscal reporting date.
CREATE INDEX IF NOT EXISTS idx_yahoo_quarterly_balance_sheet_date
    ON landing.yahoo_quarterly_balance_sheet (date DESC);

-- Supports monitoring recent ingestion activity.
CREATE INDEX IF NOT EXISTS idx_yahoo_quarterly_balance_sheet_ingested_at
    ON landing.yahoo_quarterly_balance_sheet (ingested_at DESC);