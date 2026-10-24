{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging model: Clean and standardize raw prices data
-- Source: raw.yahoo_prices_raw
-- Purpose: Deduplicate, validate, and standardize before transformations

WITH source AS (
    SELECT
        ticker,
        date,
        open,
        high,
        low,
        close,
        volume,
        adj_close,
        ingested_at,
        created_at
    FROM {{ source('raw', 'yahoo_prices_raw') }}
    WHERE date >= '{{ var("start_date") }}'
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY ticker, date
            ORDER BY ingested_at DESC
        ) as rn
    FROM source
),

cleaned AS (
    SELECT
        ticker,
        date,
        CAST(open AS NUMERIC(10, 2)) as open,
        CAST(high AS NUMERIC(10, 2)) as high,
        CAST(low AS NUMERIC(10, 2)) as low,
        CAST(close AS NUMERIC(10, 2)) as close,
        CAST(volume AS BIGINT) as volume,
        CAST(adj_close AS NUMERIC(10, 2)) as adj_close,
        ingested_at,
        created_at,
        -- Add data quality flags
        CASE WHEN high < low THEN FALSE ELSE TRUE END as is_valid_high_low,
        CASE WHEN close > 0 AND open > 0 AND high > 0 AND low > 0 THEN TRUE ELSE FALSE END as is_price_valid,
        CASE WHEN volume >= 0 THEN TRUE ELSE FALSE END as is_volume_valid
    FROM deduplicated
    WHERE rn = 1
)

SELECT * FROM cleaned
