{{
  config(
    materialized='table',
    schema='marts',
    indexes=[
      {'columns': ['ticker', 'date'], 'type': 'btree'},
      {'columns': ['ticker'], 'type': 'btree'},
    ]
  )
}}

-- Mart model: Fact table for stock prices
-- Source: stg_prices, int_returns, int_volatility
-- Purpose: Comprehensive price data for API consumption and visualization

WITH prices AS (
    SELECT
        ticker,
        date,
        open,
        high,
        low,
        close,
        volume,
        adj_close
    FROM {{ ref('stg_prices') }}
),

returns AS (
    SELECT
        ticker,
        date,
        daily_return,
        weekly_return,
        monthly_return,
        annual_return
    FROM {{ ref('int_returns') }}
),

volatility AS (
    SELECT
        ticker,
        date,
        volatility_20d,
        volatility_60d,
        volatility_252d
    FROM {{ ref('int_volatility') }}
),

combined AS (
    SELECT
        p.ticker,
        p.date,
        p.open,
        p.high,
        p.low,
        p.close,
        p.volume,
        p.adj_close,
        r.daily_return,
        r.weekly_return,
        r.monthly_return,
        r.annual_return,
        v.volatility_20d,
        v.volatility_60d,
        v.volatility_252d,
        -- Price change calculations
        (p.close - p.open) as price_change,
        ((p.close - p.open) / p.open) as price_change_pct,
        -- High-low range
        (p.high - p.low) as trading_range,
        ((p.high - p.low) / p.close) as trading_range_pct,
        -- Days since this date
        CURRENT_DATE - p.date as days_since_date,
        CURRENT_TIMESTAMP as updated_at
    FROM prices p
    LEFT JOIN returns r ON p.ticker = r.ticker AND p.date = r.date
    LEFT JOIN volatility v ON p.ticker = v.ticker AND p.date = v.date
)

SELECT * FROM combined
