# System Architecture

Foundation Flow is a **batch-only**, **on-premises** financial analytics platform for individual stock analysis.

## Core Principles

1. **Batch Processing**: No real-time streams, predictable schedules
2. **On-Premises**: Full data control, no cloud dependencies
3. **Single Source**: Yahoo Finance API only
4. **Individual Stocks**: Focus on single-stock deep analysis
5. **Modular Design**: Independent, testable components

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (Next.js Frontend)                        │
│ - Stock dashboards, charts, search interface                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI Backend)                                 │
│ - REST endpoints, data validation, business logic            │
└────────────────────┬────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ↓              ↓              ↓
┌──────────┐  ┌────────────┐  ┌──────────────┐
│PostgreSQL│  │TimescaleDB │  │Airflow Logs  │
│ Raw Data │  │ Analytics  │  │              │
└──────────┘  └────────────┘  └──────────────┘
      ↑              ↑
      └──────┬───────┘
             ↑
┌─────────────────────────────────────────────────────────────┐
│ Transformation Layer (dbt)                                  │
│ - Cleaning, validation, aggregations, feature engineering   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↑
┌─────────────────────────────────────────────────────────────┐
│ Orchestration Layer (Apache Airflow)                         │
│ - Scheduling, dependency management, error handling         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Ingestion Layer (Yahoo Finance API)                          │
│ - Daily prices, fundamentals, historical data               │
└─────────────────────────────────────────────────────────────┘
```

## Component Overview

### 1. Data Ingestion Layer

**Purpose**: Fetch data from Yahoo Finance

**Components**:
- `airflow/dags/yahoo_fetch_daily_prices.py`: Daily OHLCV prices
- `airflow/dags/yahoo_fetch_fundamentals.py`: Weekly fundamentals
- `airflow/operators/yahoo_finance_operators.py`: Custom operators

**Schedule**:
- Prices: Daily at 6 PM ET (after market close)
- Fundamentals: Weekly on Monday at 3 AM ET

**Output**: Raw data stored in PostgreSQL `raw.*` tables

### 2. Raw Data Layer

**Purpose**: Store unmodified data from API

**Technology**: PostgreSQL

**Schema**:
- `raw.yahoo_prices_raw`: OHLCV prices with JSON responses
- `raw.yahoo_fundamentals_raw`: Fundamentals with JSON responses
- `raw.pipeline_metadata`: Pipeline execution logs

**Characteristics**:
- Immutable (append-only)
- Includes raw API responses
- Indexed for fast retrieval
- Audit trail of all ingestion

### 3. Transformation Layer

**Purpose**: Clean, validate, and enrich data

**Technology**: dbt (data build tool)

**Flow**:
```
Raw (PostgreSQL)
    ↓
Staging (Views)  - Deduplication, validation
    ↓
Intermediate (Tables) - Complex calculations
    ↓
Marts (Tables)  - Analytics-ready data
    ↓
Analytics (TimescaleDB)
```

**Models**:

| Layer | Model | Purpose |
|-------|-------|---------|
| Staging | stg_prices | Clean price data |
| Staging | stg_fundamentals | Clean fundamentals |
| Intermediate | int_returns | Calculate daily/weekly/monthly returns |
| Intermediate | int_volatility | Calculate rolling volatility |
| Marts | fact_stock_prices | Historical price data with indicators |
| Marts | fact_stock_metrics | Latest metrics snapshot |

### 4. Analytics Layer

**Purpose**: Store time-series data optimized for queries

**Technology**: TimescaleDB (PostgreSQL + hypertables)

**Schema**:
- `analytics.stock_prices` (hypertable): OHLCV + returns + volatility
- `analytics.stock_returns`: Return calculations
- `analytics.stock_volatility`: Volatility metrics
- `analytics.moving_averages`: Technical indicators
- `analytics.stock_metadata`: Dimension table
- `analytics.stock_fundamentals`: Latest fundamentals snapshot

**Optimizations**:
- Hypertables for efficient time-series queries
- Automatic compression of old data
- Continuous aggregates for pre-computed views
- Strategic indexing

### 5. API Layer

**Purpose**: Serve analytics data to frontend

**Technology**: FastAPI (Python web framework)

**Architecture**:
```
FastAPI App
  ├── Health checks
  ├── API Routes
  │   ├── GET /api/stocks
  │   ├── GET /api/stocks/{ticker}
  │   ├── GET /api/stocks/{ticker}/prices
  │   ├── GET /api/stocks/{ticker}/returns
  │   └── GET /api/stocks/search
  ├── Services (business logic)
  │   └── stock_service.py
  ├── Database (connection pooling)
  │   └── connection.py
  └── Models (Pydantic validation)
      └── schemas.py
```

**Features**:
- Connection pooling for efficiency
- Async/await for concurrency
- Pydantic validation
- OpenAPI documentation
- Error handling

### 6. Frontend Layer

**Purpose**: Visualize stock data

**Technology**: Next.js 14 + React + TypeScript

**Pages**:
- `/`: Stock search and discovery
- `/stock/[ticker]`: Individual stock dashboard

**Components**:
- PriceChart: TradingView Lightweight Charts candlesticks
- MetricsPanel: Fundamental metrics display

**Features**:
- Real-time stock search
- Interactive charts
- Responsive design
- Type-safe development

## Data Flow

```
1. Ingestion (Airflow DAG runs daily)
   └─> Yahoo Finance API
   └─> Custom operators fetch and validate
   └─> Store in raw.yahoo_prices_raw

2. Transformation (dbt models)
   └─> Staging: Clean and validate
   └─> Intermediate: Calculate metrics
   └─> Marts: Prepare for analytics

3. Analytics Layer
   └─> TimescaleDB hypertables optimize queries
   └─> Continuous aggregates pre-compute common queries

4. API Serving (FastAPI)
   └─> Queries analytics layer
   └─> Returns JSON responses
   └─> Serves with OpenAPI docs

5. Visualization (Next.js)
   └─> Calls FastAPI endpoints
   └─> Renders charts and metrics
   └─> User interacts with dashboard
```

## Key Design Decisions

### Why Batch-Only?

- **Simplicity**: No complex message queues or streaming logic
- **Debuggability**: Easier to trace data through pipeline
- **Scalability**: Works well for daily/weekly analysis
- **Maintenance**: Fewer moving parts, less infrastructure

### Why PostgreSQL + TimescaleDB?

- **Battle-tested**: Reliable, proven in production
- **Time-series optimized**: TimescaleDB designed for metrics
- **SQL**: Familiar, powerful query language
- **On-prem**: No cloud lock-in

### Why dbt?

- **Modularity**: Models can be tested independently
- **Documentation**: Auto-generates lineage and documentation
- **Testability**: Built-in data quality tests
- **Version control**: SQL files in git
- **Reusability**: Macros and sources prevent repetition

### Why FastAPI?

- **Performance**: Async support for concurrent requests
- **Documentation**: Auto-generates OpenAPI specs
- **Validation**: Pydantic models for type safety
- **Modern**: Native async/await, TypeHints
- **Simple**: Easy to understand and extend

### Why Next.js?

- **Performance**: Server-side rendering and static generation
- **DX**: Great developer experience with hot reload
- **TypeScript**: Built-in type safety
- **Ecosystem**: Rich component libraries
- **Deployment**: Easy to deploy to any server

## Deployment

### Local Development

```bash
docker compose -f infrastructure/docker-compose.yml up
# All services run locally with volumes for live reloading
```

### On-Premises Production

1. Deploy on Ubuntu/CentOS server
2. Use Docker Compose or Kubernetes
3. Configure persistent volumes for databases
4. Set up monitoring and backups
5. Use systemd or container orchestration for restarts

### Not Recommended

- Cloud deployments (defeats purpose of on-prem)
- Hybrid cloud/on-prem setups (adds complexity)
- Streaming architectures (unnecessary)
- Multiple data sources (maintain single source)

## Monitoring

### Key Metrics

- **Ingestion**: Records processed, ingestion latency, errors
- **Transformation**: dbt run time, model test failures, data quality
- **API**: Request latency, error rates, throughput
- **Frontend**: Page load time, chart render time, errors

### Health Checks

```bash
# Database connectivity
docker compose exec postgres pg_isready

# Airflow DAG status
curl http://localhost:8080/api/experimental/dags

# API health
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000
```

## Security

### Current Implementation (Development)

- No authentication/authorization
- No SSL/TLS
- CORS allows all origins

### Production Recommendations

- Add API authentication (JWT or OAuth2)
- Enable SSL/TLS everywhere
- Restrict CORS to frontend domain
- Database encryption at rest and transit
- Network isolation and firewalls
- Regular security audits

## Scalability

### Current Limits

- LocalExecutor in Airflow (1 DAG at a time)
- Direct database connections (no connection pooling server)
- Single machine deployment

### Scaling Strategies

1. **Airflow**: Switch to Kubernetes/Celery executor
2. **Databases**: Read replicas, sharding
3. **API**: Load balancing, horizontal scaling
4. **Frontend**: CDN for static assets
5. **Data**: Partitioning by ticker or time

## Related Documentation

- [Data Flow Diagram](data_flow.md)
- [Database Schema Design](schema_design.md)
- [Onboarding Guide](onboarding.md)
- [Backend Architecture](../backend/README.md)
- [Airflow Documentation](../airflow/README.md)
- [dbt Documentation](../dbt/README.md)
