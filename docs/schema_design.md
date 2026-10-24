# Database Schema Design

Complete database schema for Foundation Flow across all layers.

## PostgreSQL Raw Layer

Raw data ingested directly from Yahoo Finance API.

### Schema: raw

#### Table: yahoo_prices_raw

Immutable storage of OHLCV prices from Yahoo Finance.

```sql
CREATE TABLE raw.yahoo_prices_raw (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(10, 2),
    raw_response JSONB,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, date)
);
```

**Indexes**:
- `(ticker, date)`: For fast lookups by ticker + date range
- `(ticker)`: For ticker-only queries
- `(ingested_at)`: For recent data queries

**Data Types**:
- `NUMERIC(10, 2)`: Prices (supports up to $99,999,999.99)
- `BIGINT`: Volume (supports large trading volumes)
- `JSONB`: Full API response for audit trail
- `TIMESTAMP WITH TIME ZONE`: Timestamping for consistency

**Characteristics**:
- **Idempotent**: UPSERT on (ticker, date)
- **Immutable**: Never delete, only insert/update
- **Versioned**: raw_response stores original data
- **Sparse**: Some columns can be NULL

#### Table: yahoo_fundamentals_raw

Latest snapshot of fundamental metrics.

```sql
CREATE TABLE raw.yahoo_fundamentals_raw (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL UNIQUE,
    market_cap BIGINT,
    pe_ratio NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 4),
    earnings_per_share NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low NUMERIC(10, 2),
    average_volume BIGINT,
    beta NUMERIC(5, 3),
    raw_response JSONB,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `(ticker)`: Primary lookup
- `(ingested_at)`: For recent data

#### Table: pipeline_metadata

Audit trail of pipeline execution.

```sql
CREATE TABLE raw.pipeline_metadata (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20),
    status VARCHAR(50) NOT NULL,  -- 'pending', 'running', 'success', 'failure'
    rows_processed INTEGER,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**:
- `(status)`: For failure investigation
- `(created_at)`: For audit trail

## TimescaleDB Analytics Layer

Time-series optimized data for analytics and API serving.

### Schema: analytics

#### Hypertable: stock_prices

Main hypertable for OHLCV + indicators.

```sql
CREATE TABLE analytics.stock_prices (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('analytics.stock_prices', 'time');
```

**Hypertable Configuration**:
- **Time Column**: `time` (required for hypertables)
- **Chunk Interval**: Auto-tuned (typically 1 week)
- **Compression**: Enabled for data > 30 days old
- **Continuous Aggregates**: Pre-computed 1D OHLCV

**Indexes**:
- `(ticker, time DESC)`: For ticker + time range queries

**Partitioning Strategy**:
- **Time-based**: Automatic by TimescaleDB
- **Compression**: Older data (>30 days) automatically compressed

#### Table: stock_returns

Return calculations for different periods.

```sql
CREATE TABLE analytics.stock_returns (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    daily_return NUMERIC(10, 6),
    weekly_return NUMERIC(10, 6),
    monthly_return NUMERIC(10, 6),
    annual_return NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('analytics.stock_returns', 'time');
```

**Calculations**:
- **Daily Return**: $(close_t - close_{t-1}) / close_{t-1}$
- **Weekly Return**: $(close_t - close_{t-5d}) / close_{t-5d}$
- **Monthly Return**: $(close_t - close_{t-20d}) / close_{t-20d}$
- **Annual Return**: $(close_t - close_{t-252d}) / close_{t-252d}$

#### Table: stock_volatility

Rolling volatility windows.

```sql
CREATE TABLE analytics.stock_volatility (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    volatility_20d NUMERIC(10, 6),
    volatility_60d NUMERIC(10, 6),
    volatility_252d NUMERIC(10, 6),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('analytics.stock_volatility', 'time');
```

**Calculation**: Annualized standard deviation = $\sigma(returns) \times \sqrt{252}$

#### Table: moving_averages

Technical indicators.

```sql
CREATE TABLE analytics.moving_averages (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    ma_20 NUMERIC(10, 2),
    ma_50 NUMERIC(10, 2),
    ma_200 NUMERIC(10, 2),
    source_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('analytics.moving_averages', 'time');
```

#### Dimension Table: stock_metadata

Reference data (not time-series).

```sql
CREATE TABLE analytics.stock_metadata (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(100),
    currency VARCHAR(10),
    market_cap BIGINT,
    first_price_date DATE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Dimension Table: stock_fundamentals

Latest fundamentals snapshot.

```sql
CREATE TABLE analytics.stock_fundamentals (
    ticker VARCHAR(20) PRIMARY KEY,
    pe_ratio NUMERIC(10, 2),
    earnings_per_share NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 4),
    book_value NUMERIC(15, 2),
    price_to_book NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low NUMERIC(10, 2),
    average_volume BIGINT,
    beta NUMERIC(5, 3),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Continuous Aggregates

Pre-computed daily OHLCV for fast queries.

```sql
CREATE MATERIALIZED VIEW analytics.daily_ohlcv AS
SELECT
    time_bucket('1 day', time) as day,
    ticker,
    first(open) as open,
    max(high) as high,
    min(low) as low,
    last(close) as close,
    sum(volume) as volume
FROM analytics.stock_prices
GROUP BY day, ticker;
```

## dbt Models Schema

### Staging Models

**stg_prices**: Cleaned raw prices (VIEW)

```
ticker: VARCHAR
date: DATE
open, high, low, close: NUMERIC(10, 2)
volume: BIGINT
is_valid_high_low: BOOLEAN
is_price_valid: BOOLEAN
is_volume_valid: BOOLEAN
```

**stg_fundamentals**: Cleaned fundamentals (VIEW)

```
ticker: VARCHAR
market_cap, pe_ratio, etc: Various
is_market_cap_valid: BOOLEAN
is_pe_ratio_valid: BOOLEAN
```

### Intermediate Models

**int_returns**: Calculated returns (TABLE)

```
ticker: VARCHAR
date: DATE
daily_return: NUMERIC(10, 6)
weekly_return: NUMERIC(10, 6)
monthly_return: NUMERIC(10, 6)
annual_return: NUMERIC(10, 6)
```

**int_volatility**: Calculated volatility (TABLE)

```
ticker: VARCHAR
date: DATE
volatility_20d: NUMERIC(10, 6)
volatility_60d: NUMERIC(10, 6)
volatility_252d: NUMERIC(10, 6)
```

### Mart Models

**fact_stock_prices**: Historical prices (TABLE)

```
ticker: VARCHAR
date: DATE
open, high, low, close: NUMERIC(10, 2)
volume: BIGINT
daily_return, volatility_*: NUMERIC(10, 6)
price_change, price_change_pct: NUMERIC(10, 6)
trading_range, trading_range_pct: NUMERIC(10, 6)
```

**fact_stock_metrics**: Latest metrics (TABLE)

```
ticker: VARCHAR (PRIMARY KEY)
current_price: NUMERIC(10, 2)
market_cap: BIGINT
pe_ratio, beta, volatility_*: NUMERIC(10, 6)
latest_price_date: DATE
data_completeness: VARCHAR
updated_at: TIMESTAMP
```

## Data Types Reference

| Type | Usage | Range |
|------|-------|-------|
| `VARCHAR(20)` | Ticker | Up to 20 characters |
| `DATE` | Trading dates | Full date |
| `TIMESTAMP WITH TIME ZONE` | Audit trail | Precise timing |
| `NUMERIC(10, 2)` | Prices | Up to $99,999,999.99 |
| `NUMERIC(10, 6)` | Returns/Volatility | Up to 9999.999999 |
| `BIGINT` | Volume | Up to 9,223,372,036,854,775,807 |
| `JSONB` | Raw responses | Full API data |
| `BOOLEAN` | Quality flags | TRUE/FALSE |

## Performance Considerations

### Indexing Strategy

```
PostgreSQL (raw):
  - Single unique: (ticker, date)
  - Fast lookups: (ticker), (ingested_at)
  
TimescaleDB (analytics):
  - Hypertable chunking on time
  - Index: (ticker, time DESC)
  - Continuous aggregates pre-compute daily OHLCV
```

### Query Patterns

```
Frequent:
  - SELECT * FROM fact_stock_prices WHERE ticker = ? AND date > ?
  - SELECT * FROM fact_stock_metrics WHERE ticker = ?
  
Less Frequent:
  - SELECT * FROM raw.yahoo_prices_raw (audit)
  - SELECT DISTINCT ticker FROM ... (discovery)
```

### Scaling Recommendations

1. **Add read replicas** for analytics queries
2. **Partition raw data** by year (e.g., yahoo_prices_raw_2024)
3. **Archive old data** (>5 years) to cold storage
4. **Materialized views** for common aggregations

## Related Documentation

- [System Architecture](architecture.md)
- [Data Flow](data_flow.md)
- [dbt Schema Tests](../dbt/models/schema.yml)
