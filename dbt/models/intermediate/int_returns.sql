{{
  config(
    materialized='table',
    schema='intermediate',
    indexes=[
      {'columns': ['ticker', 'date'], 'type': 'btree'},
    ]
  )
}}

-- Intermediate model: Calculate daily returns
-- Source: stg_prices
-- Purpose: Calculate various return metrics for analysis

WITH prices AS (
    SELECT
        *,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close,
        LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date) as close_5d_ago,
        LAG(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_20d_ago,
        LAG(close, 252) OVER (PARTITION BY ticker ORDER BY date) as close_252d_ago
    FROM {{ ref('stg_prices') }}
    WHERE is_price_valid = TRUE
),

returns AS (
    SELECT
        ticker,
        date,
        close,
        -- Daily return calculation: (today_close - prev_close) / prev_close
        CASE
            WHEN prev_close IS NOT NULL AND prev_close > 0
            THEN ((close - prev_close) / prev_close)
            ELSE NULL
        END as daily_return,
        -- Weekly return
        CASE
            WHEN close_5d_ago IS NOT NULL AND close_5d_ago > 0
            THEN ((close - close_5d_ago) / close_5d_ago)
            ELSE NULL
        END as weekly_return,
        -- Monthly return
        CASE
            WHEN close_20d_ago IS NOT NULL AND close_20d_ago > 0
            THEN ((close - close_20d_ago) / close_20d_ago)
            ELSE NULL
        END as monthly_return,
        -- Annual return
        CASE
            WHEN close_252d_ago IS NOT NULL AND close_252d_ago > 0
            THEN ((close - close_252d_ago) / close_252d_ago)
            ELSE NULL
        END as annual_return,
        created_at
    FROM prices
)

SELECT * FROM returns
