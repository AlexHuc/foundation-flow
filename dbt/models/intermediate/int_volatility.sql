{{
  config(
    materialized='table',
    schema='intermediate',
    indexes=[
      {'columns': ['ticker', 'date'], 'type': 'btree'},
    ]
  )
}}

-- Intermediate model: Calculate historical volatility
-- Source: int_returns
-- Purpose: Calculate rolling volatility windows for risk assessment

WITH daily_returns AS (
    SELECT
        ticker,
        date,
        daily_return,
        -- Calculate squared returns for variance
        daily_return * daily_return as squared_return
    FROM {{ ref('int_returns') }}
    WHERE daily_return IS NOT NULL
),

volatility_windows AS (
    SELECT
        ticker,
        date,
        -- 20-day (1 month) volatility
        STDDEV_POP(daily_return) OVER (
            PARTITION BY ticker
            ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) * SQRT(252) as volatility_20d,
        -- 60-day (3 month) volatility
        STDDEV_POP(daily_return) OVER (
            PARTITION BY ticker
            ORDER BY date
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) * SQRT(252) as volatility_60d,
        -- 252-day (1 year) volatility
        STDDEV_POP(daily_return) OVER (
            PARTITION BY ticker
            ORDER BY date
            ROWS BETWEEN 251 PRECEDING AND CURRENT ROW
        ) * SQRT(252) as volatility_252d
    FROM daily_returns
)

SELECT
    ticker,
    date,
    ROUND(CAST(volatility_20d AS NUMERIC), 6) as volatility_20d,
    ROUND(CAST(volatility_60d AS NUMERIC), 6) as volatility_60d,
    ROUND(CAST(volatility_252d AS NUMERIC), 6) as volatility_252d,
    CASE
        WHEN volatility_20d IS NOT NULL THEN TRUE
        ELSE FALSE
    END as is_calculated
FROM volatility_windows
