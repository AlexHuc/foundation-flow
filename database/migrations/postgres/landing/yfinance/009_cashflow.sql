-- ============================================================
-- Table: landing.yahoo_cashflow
-- Purpose: Store Yahoo Finance annual cash flow statements.
-- ============================================================

CREATE TABLE IF NOT EXISTS landing.yahoo_cashflow (
    ticker                                                 VARCHAR(10) NOT NULL,
    date                                                   DATE NOT NULL,

    -- Free cash flow and capital expenditure
    free_cash_flow                                         BIGINT,
    capital_expenditure                                    BIGINT,

    -- Supplemental cash flow information
    income_tax_paid_supplemental_data                      BIGINT,
    end_cash_position                                      BIGINT,
    beginning_cash_position                                BIGINT,
    effect_of_exchange_rate_changes                        BIGINT,
    changes_in_cash                                        BIGINT,

    -- Financing cash flow
    financing_cash_flow                                    BIGINT,
    cash_flow_from_continuing_financing_activities         BIGINT,
    net_other_financing_charges                            BIGINT,
    proceeds_from_stock_option_exercised                   BIGINT,

    -- Stock issuance and repurchases
    repurchase_of_capital_stock                            BIGINT,
    issuance_of_capital_stock                              BIGINT,
    net_preferred_stock_issuance                           BIGINT,
    preferred_stock_issuance                               BIGINT,
    net_common_stock_issuance                              BIGINT,
    common_stock_payments                                  BIGINT,
    common_stock_issuance                                  BIGINT,

    -- Investing cash flow
    investing_cash_flow                                    BIGINT,
    cash_flow_from_continuing_investing_activities         BIGINT,
    net_investment_purchase_and_sale                       BIGINT,
    sale_of_investment                                     BIGINT,
    purchase_of_investment                                 BIGINT,
    net_business_purchase_and_sale                         BIGINT,
    purchase_of_business                                   BIGINT,
    net_ppe_purchase_and_sale                              BIGINT,
    purchase_of_ppe                                        BIGINT,

    -- Operating cash flow
    operating_cash_flow                                    BIGINT,
    cash_flow_from_continuing_operating_activities         BIGINT,

    -- Working capital changes
    change_in_working_capital                              BIGINT,
    change_in_other_working_capital                        BIGINT,
    change_in_other_current_assets                         BIGINT,
    change_in_payables_and_accrued_expense                 BIGINT,
    change_in_accrued_expense                              BIGINT,
    change_in_payable                                      BIGINT,
    change_in_account_payable                              BIGINT,
    change_in_prepaid_assets                               BIGINT,
    change_in_inventory                                    BIGINT,
    change_in_receivables                                  BIGINT,
    changes_in_account_receivables                         BIGINT,

    -- Non-cash adjustments
    stock_based_compensation                               BIGINT,
    asset_impairment_charge                                BIGINT,
    depreciation_amortization_depletion                    BIGINT,
    depreciation_and_amortization                          BIGINT,
    amortization_cash_flow                                 BIGINT,
    amortization_of_intangibles                            BIGINT,
    depreciation                                           BIGINT,
    operating_gains_losses                                 BIGINT,
    gain_loss_on_investment_securities                     BIGINT,

    -- Net income reconciliation
    net_income_from_continuing_operations                  BIGINT,

    ingested_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_yahoo_cashflow
        PRIMARY KEY (ticker, date)
);

-- Supports queries across tickers by reporting date.
CREATE INDEX IF NOT EXISTS idx_yahoo_cashflow_date
    ON landing.yahoo_cashflow (date DESC);

-- Supports monitoring recently ingested cash flow data.
CREATE INDEX IF NOT EXISTS idx_yahoo_cashflow_ingested_at
    ON landing.yahoo_cashflow (ingested_at DESC);