{{
  config(
    materialized='table',
    schema='marts',
    indexes=[
      {'columns': ['ticker'], 'type': 'btree'},
    ]
  )
}}

-- Mart model: Fact table for stock metrics and fundamentals
-- Source: stg_prices, stg_fundamentals, int_returns, int_volatility
-- Purpose: Latest stock metrics and fundamental data for API consumption

WITH latest_prices AS (
    SELECT
        ticker,
        close as latest_price,
        date as latest_price_date,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
    FROM {{ ref('stg_prices') }}
    WHERE is_price_valid = TRUE
),

latest_fundamentals AS (
    SELECT
        ticker,
        market_cap,
        pe_ratio,
        dividend_yield,
        earnings_per_share,
        fifty_two_week_high,
        fifty_two_week_low,
        average_volume,
        beta,
        created_at as fundamentals_date
    FROM {{ ref('stg_fundamentals') }}
),

latest_returns AS (
    SELECT
        ticker,
        daily_return,
        weekly_return,
        monthly_return,
        annual_return,
        date as returns_date,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
    FROM {{ ref('int_returns') }}
    WHERE daily_return IS NOT NULL
),

latest_volatility AS (
    SELECT
        ticker,
        volatility_20d,
        volatility_60d,
        volatility_252d,
        date as volatility_date,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
    FROM {{ ref('int_volatility') }}
    WHERE is_calculated = TRUE
),

price_metrics AS (
    SELECT
        ticker,
        latest_price,
        latest_price_date,
        -- Calculate performance against 52-week high/low
        latest_price as current_price,
        ROUND(CAST((latest_price - f.fifty_two_week_low) / (f.fifty_two_week_high - f.fifty_two_week_low) * 100 AS NUMERIC), 2) as fifty_two_week_position_pct
    FROM latest_prices lp
    LEFT JOIN latest_fundamentals f ON lp.ticker = f.ticker
    WHERE lp.rn = 1
)

SELECT
    pm.ticker,
    pm.current_price,
    pm.latest_price_date,
    f.market_cap,
    f.pe_ratio,
    f.dividend_yield,
    f.earnings_per_share,
    f.fifty_two_week_high,
    f.fifty_two_week_low,
    pm.fifty_two_week_position_pct,
    f.average_volume,
    f.beta,
    r.daily_return,
    r.weekly_return,
    r.monthly_return,
    r.annual_return,
    v.volatility_20d,
    v.volatility_60d,
    v.volatility_252d,
    CASE
        WHEN f.market_cap IS NOT NULL THEN 'complete'
        ELSE 'partial'
    END as data_completeness,
    CURRENT_TIMESTAMP as updated_at
FROM price_metrics pm
LEFT JOIN latest_fundamentals f ON pm.ticker = f.ticker
LEFT JOIN latest_returns r ON pm.ticker = r.ticker AND r.rn = 1
LEFT JOIN latest_volatility v ON pm.ticker = v.ticker AND v.rn = 1
