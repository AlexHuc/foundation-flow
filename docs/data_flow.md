# Data Flow Diagram

Complete data flow from ingestion through visualization.

## Daily Price Ingestion Pipeline

```
8:00 PM UTC (3:00 PM ET)
        │
        ↓
┌──────────────────────┐
│ Airflow Scheduler    │ Triggers daily DAG
└──────┬───────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ yahoo_fetch_daily_prices DAG             │
├──────────────────────────────────────────┤
│ Task 1: Log DAG info                     │
│ Task 2-N: Fetch prices for each ticker   │
│          (AAPL, MSFT, GOOGL, AMZN, etc.) │ [Parallel]
│ Task N+1: Verify data quality            │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ FetchYahooFinancePricesOperator           │ For each ticker:
├──────────────────────────────────────────┤ - Fetch last 5 years
│ 1. Call Yahoo Finance API                │ - Get OHLCV data
│ 2. Validate response                     │ - Check data quality
│ 3. Transform to DataFrame                │ - Handle retries
│ 4. Upsert to PostgreSQL                  │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ PostgreSQL raw.yahoo_prices_raw          │ Raw storage
├──────────────────────────────────────────┤ - Immutable
│ ticker│date      │open│high│low│close   │ - Versioned
│ AAPL  │2024-01-15│185│186│185│186       │ - Full history
│ AAPL  │2024-01-16│186│187│186│187       │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ dbt run (Manual or scheduled)             │ Transforms data
├──────────────────────────────────────────┤
│ Staging:        stg_prices               │
│   - Deduplication                        │
│   - Validation (prices > 0, high >= low) │
│   - Standardization                      │
│                                          │
│ Intermediate:   int_returns              │
│   - Daily return: (close - prev) / prev  │
│   - Weekly, monthly, annual returns      │
│   - Using window functions               │
│                                          │
│               int_volatility             │
│   - 20-day rolling std dev               │
│   - 60-day rolling std dev               │
│   - 252-day rolling std dev (annual)     │
│   - Annualized (* sqrt(252))             │
│                                          │
│ Marts:          fact_stock_prices        │
│   - Join prices + returns + volatility   │
│   - Ready for API consumption            │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ TimescaleDB analytics.stock_prices       │ Hypertable
├──────────────────────────────────────────┤ Time-series optimized
│ time │ ticker│ open │ close │ volume     │
│ 2024 │ AAPL  │ 185  │ 186   │ 45M        │
│ 2024 │ AAPL  │ 186  │ 187   │ 48M        │
│      │       │      │       │            │
│ Features:                                │
│ - Compression of data > 30 days          │
│ - Continuous aggregates (1D OHLCV)      │
│ - Optimized for time-range queries       │
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ FastAPI Backend                          │ REST API
├──────────────────────────────────────────┤
│ GET /api/stocks/{ticker}/prices          │
│   └─> Query TimescaleDB                  │
│   └─> Return JSON with OHLCV + indicators│
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ Next.js Frontend                         │ UI
├──────────────────────────────────────────┤
│ 1. User navigates to /stock/AAPL         │
│ 2. Frontend calls /api/stocks/AAPL/prices│
│ 3. Backend queries TimescaleDB           │
│ 4. Response: Last 90 days of prices      │
│ 5. Render candlestick chart              │
│ 6. Display metrics (P/E, volatility, etc)│
│ 7. User can zoom, pan, interact          │
└──────────────────────────────────────────┘
```

## Weekly Fundamentals Pipeline

```
Monday 3:00 AM ET (8:00 AM UTC)
        │
        ↓
┌──────────────────────────────┐
│ yahoo_fetch_fundamentals DAG │
└──────┬───────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ For each ticker:                 │
│ - Fetch fundamentals             │
│ - Market cap, P/E, Dividend, etc │
│ - Upsert to raw layer            │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ PostgreSQL raw.yahoo_fundamentals│
│ _raw                             │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ dbt stg_fundamentals             │
│ - Clean and validate             │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ TimescaleDB analytics.stock_     │
│ fundamentals (dimension table)   │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ FastAPI returns metrics          │
│ GET /api/stocks/{ticker}         │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ Frontend MetricsPanel component  │
│ Displays P/E, market cap, beta   │
└──────────────────────────────────┘
```

## Query Flow Examples

### Example 1: Get Stock Prices

```
User clicks: /stock/AAPL
           │
           ↓
Frontend: api.get('/api/stocks/AAPL/prices?days=30')
           │
           ↓
Backend: sql("SELECT * FROM marts.fact_stock_prices WHERE ticker='AAPL' AND date > NOW()-30d")
           │
           ↓
TimescaleDB: Hypertable query with index on (ticker, date)
             └─> Result: ~30 rows in <100ms
           │
           ↓
FastAPI: Returns JSON array
           │
           ↓
Frontend: TradingViewLightweightCharts renders candlesticks
           │
           ↓
User sees: Interactive price chart with 30 days of data
```

### Example 2: Search Stocks

```
User types: "APP" in search box
           │
           ↓
Frontend: api.get('/api/stocks/search?q=APP')
           │
           ↓
Backend: sql("SELECT ticker FROM marts.fact_stock_metrics WHERE ticker ILIKE 'APP%'")
           │
           ↓
TimescaleDB: Returns matching tickers
             └─> Results: ["AAPL", "APPF", "APPN"]
           │
           ↓
Frontend: Displays dropdown with results
           │
           ↓
User clicks: "AAPL" → navigates to /stock/AAPL
```

## Error Handling Flow

```
Error occurs in pipeline
           │
           ├─ Ingestion: API timeout
           │   │
           │   ├─ Retry logic: exponential backoff
           │   ├─ Log to raw.pipeline_metadata
           │   ├─ Alert (future)
           │   └─ Operator catches exception
           │
           ├─ Transformation: dbt test fails
           │   │
           │   ├─ Data quality test detects issue
           │   ├─ dbt stops with error
           │   ├─ No data written to marts
           │   └─ Alert (future)
           │
           └─ API: Database timeout
               │
               ├─ Connection retry
               ├─ Returns 503 Service Unavailable
               ├─ Frontend displays error
               └─ User sees: "Please try again later"
```

## Time Scales

- **Ingestion**: 6 PM - 11 PM ET (daily prices) + Monday 3 AM (fundamentals)
- **Transformation**: Manual (can be automated with Airflow dbt task)
- **API Response**: < 100ms for typical queries
- **Chart Render**: < 500ms for 500 data points
- **Full Pipeline**: Ingestion → Raw → dbt → Analytics: ~1-2 hours

## Data Consistency

- **Raw Layer**: Immutable, append-only, versioned
- **Analytics Layer**: Latest values, updated by dbt
- **Idempotency**: All operations can be safely rerun
- **No Transactions Needed**: Batch processing means consistency guaranteed

## Related Documentation

- [System Architecture](architecture.md)
- [Database Schema](schema_design.md)
- [Airflow DAGs](../airflow/README.md)
