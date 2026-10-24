{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging model: Clean and standardize raw fundamentals data
-- Source: raw.yahoo_fundamentals_raw
-- Purpose: Deduplicate, validate, and standardize before transformations

WITH source AS (
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
        ingested_at,
        created_at
    FROM {{ source('raw', 'yahoo_fundamentals_raw') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY ingested_at DESC
        ) as rn
    FROM source
),

cleaned AS (
    SELECT
        ticker,
        CAST(market_cap AS BIGINT) as market_cap,
        CAST(pe_ratio AS NUMERIC(10, 2)) as pe_ratio,
        CAST(dividend_yield AS NUMERIC(10, 6)) as dividend_yield,
        CAST(earnings_per_share AS NUMERIC(10, 2)) as earnings_per_share,
        CAST(fifty_two_week_high AS NUMERIC(10, 2)) as fifty_two_week_high,
        CAST(fifty_two_week_low AS NUMERIC(10, 2)) as fifty_two_week_low,
        CAST(average_volume AS BIGINT) as average_volume,
        CAST(beta AS NUMERIC(5, 3)) as beta,
        ingested_at,
        created_at,
        -- Data quality flags
        CASE WHEN market_cap > 0 THEN TRUE ELSE FALSE END as is_market_cap_valid,
        CASE WHEN pe_ratio IS NULL OR pe_ratio > 0 THEN TRUE ELSE FALSE END as is_pe_ratio_valid,
        CASE WHEN beta IS NULL OR (beta > 0 AND beta < 5) THEN TRUE ELSE FALSE END as is_beta_valid
    FROM deduplicated
    WHERE rn = 1
)

SELECT * FROM cleaned
