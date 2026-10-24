# dbt Data Transformation Layer

dbt (data build tool) orchestrates all data transformations from raw PostgreSQL data to analytics-ready tables in TimescaleDB.

## Overview

dbt handles:
- Data cleaning and validation
- Transformation logic
- Data quality testing
- Documentation and lineage
- Incremental loading strategies

## Architecture

```
Raw Layer (PostgreSQL)
    ↓ [Staging - Deduplication, validation]
    ├── stg_prices
    ├── stg_fundamentals
    ↓ [Intermediate - Calculations]
    ├── int_returns
    ├── int_volatility
    ↓ [Marts - Analytics-ready]
    ├── fact_stock_prices
    ├── fact_stock_metrics
    ↓
TimescaleDB (Analytics Layer)
```

## Directory Structure

```
dbt/
├── models/
│   ├── staging/          # Raw data cleaning
│   │   ├── stg_prices.sql
│   │   └── stg_fundamentals.sql
│   ├── intermediate/     # Complex calculations
│   │   ├── int_returns.sql
│   │   └── int_volatility.sql
│   ├── marts/            # Final analytics tables
│   │   ├── fact_stock_prices.sql
│   │   └── fact_stock_metrics.sql
│   └── schema.yml        # Data documentation & tests
├── tests/                # dbt tests
├── macros/               # Custom macros
├── dbt_project.yml       # dbt configuration
├── profiles.yml          # Database connections
└── README.md             # This file
```

## Models

### Staging Layer

Clean and standardize raw data from Yahoo Finance.

#### stg_prices
- **Source**: `raw.yahoo_prices_raw`
- **Purpose**: Clean prices, add data quality flags
- **Key Columns**:
  - `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`
  - `is_valid_high_low`: Flag if high >= low
  - `is_price_valid`: All prices > 0
  - `is_volume_valid`: Volume >= 0
- **Materialization**: View (for efficiency)

#### stg_fundamentals
- **Source**: `raw.yahoo_fundamentals_raw`
- **Purpose**: Clean fundamentals, add data quality flags
- **Key Columns**:
  - `ticker`, `market_cap`, `pe_ratio`, `dividend_yield`, `beta`
  - Quality validation flags
- **Materialization**: View

### Intermediate Layer

Calculate complex metrics for analysis.

#### int_returns
- **Source**: `stg_prices`
- **Purpose**: Calculate daily, weekly, monthly, annual returns
- **Returns Calculation**:
  ```
  daily_return = (today_close - yesterday_close) / yesterday_close
  weekly_return = (close - close_5d_ago) / close_5d_ago
  monthly_return = (close - close_20d_ago) / close_20d_ago
  annual_return = (close - close_252d_ago) / close_252d_ago
  ```
- **Materialization**: Table (for performance)

#### int_volatility
- **Source**: `int_returns`
- **Purpose**: Calculate rolling volatility windows
- **Volatility Calculations**:
  - 20-day volatility (monthly)
  - 60-day volatility (quarterly)
  - 252-day volatility (annual)
  - Annualized using $\sqrt{252}$ trading days per year
- **Materialization**: Table

### Mart Layer

Final analytics tables for API and visualization.

#### fact_stock_prices
- **Purpose**: Comprehensive historical price data
- **Columns**: All OHLCV + calculated metrics + returns + volatility
- **Use Cases**:
  - Candlestick charts
  - Technical analysis
  - Historical lookback queries
- **Partitioning**: By ticker and date
- **Materialization**: Table with indexes

#### fact_stock_metrics
- **Purpose**: Latest stock metrics and fundamentals
- **Columns**:
  - Current price, market cap, P/E ratio
  - 52-week high/low and position
  - Latest returns and volatility
  - Beta, dividend yield
- **Use Cases**:
  - Stock comparison
  - Dashboard metrics
  - Latest data queries
- **Unique**: One row per ticker (latest values)
- **Materialization**: Table with indexes

## Configuration

### dbt_project.yml

Main dbt configuration:

```yaml
name: 'foundation_flow'
version: '1.0.0'
config-version: 2

# Model materialization by layer
models:
  foundation_flow:
    staging:
      +materialized: view      # Lightweight, computed on demand
    intermediate:
      +materialized: table     # Materialized for complex calculations
    marts:
      +materialized: table     # Materialized for query performance

# Model-level variables
vars:
  start_date: '2020-01-01'
  lookback_days: 252          # 1 trading year
  ma_short: 20                # Short-term moving average
  ma_medium: 50               # Medium-term moving average
  ma_long: 200                # Long-term moving average
```

### profiles.yml

Database connections for dbt (configure for your setup):

```yaml
foundation_flow:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      user: airflow
      password: airflow
      port: 5432
      dbname: analytics
      schema: public
      threads: 4
      keepalives_idle: 0

    prod:
      type: postgres
      host: timescale
      user: postgres
      password: postgres
      port: 5432
      dbname: analytics_prod
      schema: public
      threads: 8
      keepalives_idle: 0
```

## Running dbt

### Installation

```bash
# Install dbt with PostgreSQL adapter
pip install dbt-core dbt-postgres

# Verify installation
dbt --version
```

### Commands

```bash
# Parse all models
dbt parse

# Run all models
dbt run

# Run specific model
dbt run --models stg_prices

# Run model and downstream dependencies
dbt run --models +fact_stock_prices

# Run model and upstream dependencies
dbt run --models fact_stock_prices+

# Run with specific target (dev/prod)
dbt run --target prod

# Generate documentation
dbt docs generate

# View documentation
dbt docs serve
```

### Testing

```bash
# Run all tests
dbt test

# Run tests for specific model
dbt test --models stg_prices

# Run specific test
dbt test --models stg_prices --select +data_integrity

# View test results
dbt test --store-failures
```

### Development Workflow

```bash
# 1. Run specific model in development
dbt run --models stg_prices --target dev

# 2. Test the model
dbt test --models stg_prices --target dev

# 3. View lineage
dbt docs generate
dbt docs serve  # Then visit http://localhost:8000

# 4. Deploy to production
dbt run --target prod
dbt test --target prod
```

## Data Tests

dbt includes data quality tests defined in `schema.yml`:

### Generic Tests
- `not_null`: Column must have values
- `unique`: Column values must be distinct
- `accepted_values`: Column values must be in list
- `relationships`: Foreign key relationship validation

### Example Tests

```yaml
# Test ticker is not null and has valid values
- name: ticker
  tests:
    - not_null
    - relationships:
        to: source('raw', 'yahoo_fundamentals_raw')
        field: ticker

# Test prices are positive
- name: close
  tests:
    - not_null
    - accepted_values:
        values: ["> 0"]
```

### Running Tests

```bash
# Run all tests
dbt test

# Run tests, store failures
dbt test --store-failures

# Check test results
SELECT * FROM dbt_schema._dbt_internal_tests
```

## Documentation

dbt auto-generates documentation from:
- Model SQL files
- Column descriptions in schema.yml
- Test definitions

### Generate Docs

```bash
dbt docs generate
dbt docs serve  # Starts local server on http://localhost:8000
```

### View Lineage

In generated docs, click "Lineage" to see:
- Data flow from raw → staging → intermediate → marts
- Model dependencies
- Test coverage

## Performance Optimization

### Indexes

Models automatically create indexes:

```sql
-- Indexes on fact tables for fast queries
CREATE INDEX idx_fact_prices_ticker_date 
  ON fact_stock_prices(ticker, date DESC);

CREATE INDEX idx_fact_metrics_ticker 
  ON fact_stock_metrics(ticker);
```

### Materialization Strategy

```yaml
staging:
  +materialized: view        # No storage, computed on demand
  # Best for simple transformations, less storage

intermediate:
  +materialized: table       # Stored in database
  # Best for complex calculations, improves downstream performance

marts:
  +materialized: table       # Stored in database with indexes
  # Best for API serving, query performance critical
```

### Query Optimization

dbt generates efficient SQL:
- Deduplication using window functions
- Efficient joins with proper indexes
- Aggregate calculations using SQL window functions

## Troubleshooting

### dbt Commands Fail

```bash
# Verify database connection
dbt debug

# Check dbt version
dbt --version

# Validate project
dbt parse
```

### Model Compilation Errors

```bash
# Check SQL syntax
dbt parse

# View compiled SQL
dbt compile --models stg_prices
# Check target/compiled/foundation_flow/models/staging/stg_prices.sql
```

### Test Failures

```bash
# Run specific test
dbt test --models stg_prices

# View failure details
SELECT * FROM dbt_schema.stg_prices_tests_failure
```

### Slow Queries

```bash
# Add query timing
dbt run --debug

# Check TimescaleDB query plans
EXPLAIN ANALYZE SELECT * FROM fact_stock_prices;

# Add missing indexes
dbt run-operation create_indexes
```

## Advanced

### Custom Macros

Create reusable SQL functions in `macros/`:

```sql
-- macros/generate_alias.sql
{% macro generate_alias(relation) %}
    {%- if execute -%}
        {{ relation.schema }}.{{ relation.name }}
    {%- endif -%}
{% endmacro %}
```

### Incremental Models

For large datasets, use incremental load:

```sql
{{
  config(
    materialized='incremental',
    unique_key=['ticker', 'date']
  )
}}

SELECT * FROM raw.yahoo_prices_raw

{% if execute %}
  WHERE date > (SELECT MAX(date) FROM {{ this }})
{% endif %}
```

### Custom Tests

Define custom tests in `tests/`:

```sql
-- tests/test_price_accuracy.sql
SELECT ticker, date, COUNT(*)
FROM fact_stock_prices
GROUP BY ticker, date
HAVING COUNT(*) > 1
```

## Integration with Airflow

dbt runs as task in Airflow:

```python
# airflow/dags/dbt_transformation.py
from airflow.operators.bash import BashOperator

dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='cd /path/to/dbt && dbt run',
)
```

## Links

- [dbt Documentation](https://docs.getdbt.com/)
- [Model Best Practices](https://docs.getdbt.com/guides/best-practices)
- [Testing Guide](https://docs.getdbt.com/docs/build/tests)
- [System Architecture](../docs/architecture.md)
- [Database Schema](../docs/schema_design.md)
