# Onboarding Guide

Step-by-step guide to understand and deploy Foundation Flow.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understand the Architecture](#understand-the-architecture)
3. [Local Development Setup](#local-development-setup)
4. [Running Your First Pipeline](#running-your-first-pipeline)
5. [Exploring the Data](#exploring-the-data)
6. [Development Workflow](#development-workflow)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- Docker & Docker Compose (v20.10+)
- Git
- macOS, Linux, or WSL2 on Windows
- 4+ GB available disk space
- 2+ GB available RAM

### Optional

- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)
- PostgreSQL client tools (`psql`)

### Hardware

- **Development**: 2+ CPU, 4+ GB RAM, 50+ GB disk
- **Small production**: 4+ CPU, 8+ GB RAM, 100+ GB disk

## Understand the Architecture

Before diving in, understand what Foundation Flow does:

### The Core Idea

```
Yahoo Finance Data
    ↓ [Ingested daily by Airflow]
PostgreSQL Raw Layer
    ↓ [Transformed by dbt]
TimescaleDB Analytics Layer
    ↓ [Served by FastAPI]
Next.js Frontend
    ↓ [User views stock charts]
```

### Key Components

1. **Airflow**: Orchestrates daily data ingestion
2. **dbt**: Transforms raw data into analytics-ready tables
3. **PostgreSQL + TimescaleDB**: Stores raw and processed data
4. **FastAPI**: REST API for serving data
5. **Next.js**: Stock dashboard frontend

### Read First

1. [System Architecture](architecture.md) - 10 minute read
2. [Data Flow Diagram](data_flow.md) - Visual overview
3. Component READMEs:
   - [Airflow](../airflow/README.md)
   - [dbt](../dbt/README.md)
   - [Backend](../backend/README.md)
   - [Frontend](../frontend/README.md)

## Local Development Setup

### Step 1: Clone and Explore

```bash
# Clone repository
git clone <repo-url>
cd foundation-flow

# Explore structure
ls -la
cat README.md

# Look at root config files
cat infrastructure/docker-compose.yml
cat infrastructure/env.example
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp infrastructure/env.example infrastructure/.env

# Review and customize if needed (for local dev, defaults usually work)
cat infrastructure/.env
```

### Step 3: Start All Services

```bash
# From foundation-flow root directory
cd infrastructure
docker compose up -d

# Wait 2-3 minutes for all services to start
docker compose logs -f
```

### Step 4: Verify Services Running

```bash
# Check container status
docker compose ps

# All should show "running" with healthy checks passing

# Test each endpoint
curl http://localhost:8080           # Airflow (may redirect)
curl http://localhost:8000/docs      # FastAPI docs
curl http://localhost:3000           # Frontend
```

### Step 5: Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| Airflow UI | http://localhost:8080 | Monitor DAGs |
| FastAPI Docs | http://localhost:8000/docs | Interactive API |
| Frontend | http://localhost:3000 | Stock dashboard |

## Running Your First Pipeline

### Step 1: Access Airflow

```bash
# Open browser
open http://localhost:8080

# Should see DAG list
# Look for: yahoo_fetch_daily_prices, yahoo_fetch_fundamentals
```

### Step 2: Trigger Data Ingestion

```bash
# Via API
curl -X POST http://localhost:8080/api/experimental/dags/yahoo_fetch_daily_prices/dag_runs \
  -H "Content-Type: application/json" \
  -d '{"conf":{"tickers":["AAPL"]}}'

# Or in Airflow UI:
# 1. Click DAG name
# 2. Click "Trigger DAG" button
# 3. Modify config if needed
# 4. Click "Trigger"
```

### Step 3: Monitor Execution

```bash
# In Airflow UI, watch task progress
# Green = success
# Red = failed
# Yellow = running

# Or via CLI
docker compose exec airflow-webserver airflow tasks list yahoo_fetch_daily_prices

# View logs
docker compose logs airflow-scheduler -f
```

### Step 4: Wait for Completion

Typical pipeline runtime:
- Fetch prices for 8 tickers: 2-5 minutes
- Verify data quality: < 1 minute
- Total: ~5-10 minutes

## Exploring the Data

### Step 1: Connect to PostgreSQL (Raw Layer)

```bash
# Via Docker
docker compose exec postgres psql -U airflow -d analytics

# Once in psql:
SELECT ticker, MAX(date) as latest_date, COUNT(*) as records
FROM raw.yahoo_prices_raw
GROUP BY ticker;
```

### Step 2: Connect to TimescaleDB (Analytics Layer)

```bash
# Via Docker
docker compose exec timescale psql -U postgres -d analytics_prod

# Once in psql:
SELECT * FROM marts.fact_stock_metrics LIMIT 5;
SELECT * FROM marts.fact_stock_prices WHERE ticker='AAPL' LIMIT 10;
```

### Step 3: Query via FastAPI

```bash
# Get all available stocks
curl http://localhost:8000/api/stocks

# Get specific stock metrics
curl http://localhost:8000/api/stocks/AAPL

# Get 30 days of prices
curl "http://localhost:8000/api/stocks/AAPL/prices?days=30"

# Search stocks
curl "http://localhost:8000/api/stocks/search?q=APP"
```

### Step 4: View in Frontend

```bash
# Open http://localhost:3000
# 1. Type ticker in search box
# 2. Click result or navigate to /stock/AAPL
# 3. See candlestick chart and metrics

# Interactive:
# - Zoom chart
# - Pan left/right
# - View fundamental metrics
```

## Development Workflow

### Adding a New Stock to Monitor

1. **Update Airflow DAG**:

```python
# In airflow/dags/yahoo_fetch_daily_prices.py
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NFLX', 'META', 'NVIDIA', 'NVDA']  # Add NVDA
```

2. **Commit and redeploy**:

```bash
git add airflow/dags/yahoo_fetch_daily_prices.py
git commit -m "Add NVDA to daily price tracking"

# Airflow will auto-discover within minutes
```

3. **Verify in Airflow UI**:

Check that NVDA appears in task list for next run.

### Modifying dbt Transformations

1. **Create new model** in `dbt/models/marts/`:

```bash
# New SQL model
cat > dbt/models/marts/fact_stock_summary.sql << 'EOF'
{{
  config(materialized='table', schema='marts')
}}

SELECT
    ticker,
    current_price,
    annual_return,
    volatility_252d,
    market_cap
FROM {{ ref('fact_stock_metrics') }}
EOF
```

2. **Test locally**:

```bash
cd dbt
dbt run --models fact_stock_summary
dbt test --models fact_stock_summary
```

3. **Commit and deploy**:

```bash
git add dbt/models/marts/fact_stock_summary.sql
git commit -m "Add stock summary fact table"
```

### Adding New API Endpoint

1. **Define schema** in `backend/models/schemas.py`:

```python
class MyResponse(BaseModel):
    ticker: str
    value: float
```

2. **Add service function** in `backend/services/stock_service.py`:

```python
async def get_my_data(ticker: str):
    conn = await get_analytics_connection()
    row = await conn.fetchrow("SELECT ...", ticker)
    await conn.close()
    return dict(row)
```

3. **Add route** in `backend/api/stocks.py`:

```python
@router.get("/{ticker}/mydata", response_model=MyResponse)
async def my_endpoint(ticker: str):
    return await get_my_data(ticker)
```

4. **Test**:

```bash
# Restart backend
docker compose restart backend

# Test endpoint
curl http://localhost:8000/api/stocks/AAPL/mydata
```

## Troubleshooting

### Containers Won't Start

```bash
# Check for port conflicts
lsof -i :5432
lsof -i :8080
lsof -i :8000

# Clean up old containers
docker compose down -v
docker system prune -a

# Try starting again
docker compose up -d
```

### Pipeline Fails

```bash
# Check Airflow logs
docker compose logs airflow-scheduler | tail -100

# Test specific task
docker compose exec airflow-webserver \
  airflow tasks test yahoo_fetch_daily_prices fetch_prices_AAPL 2024-01-15

# Check database connectivity
docker compose exec postgres pg_isready
docker compose exec timescale pg_isready
```

### Database Connection Errors

```bash
# Verify PostgreSQL is healthy
docker compose exec postgres \
  psql -U airflow -d analytics -c "SELECT 1;"

# Check connection from backend
docker compose logs backend | grep "connection"

# Verify database schemas exist
docker compose exec postgres psql -U airflow -d analytics -c "\dt raw.*"
docker compose exec timescale psql -U postgres -d analytics_prod -c "\dt analytics.*"
```

### API Returns 404

```bash
# Check that data was ingested
docker compose exec postgres psql -U airflow -d analytics << EOF
SELECT COUNT(*) FROM raw.yahoo_prices_raw;
EOF

# Check dbt transformations ran
docker compose exec postgres psql -U airflow -d analytics << EOF
SELECT * FROM marts.fact_stock_metrics LIMIT 1;
EOF

# If empty, run dbt manually
docker compose exec backend dbt run --target dev
```

### Frontend Shows Blank

```bash
# Check browser console (F12)
# Look for CORS or API errors

# Check frontend logs
docker compose logs frontend

# Verify API is responding
curl -v http://localhost:8000/api/stocks

# Restart frontend
docker compose restart frontend
```

## Next Steps

### Learn More

1. [System Architecture Deep Dive](architecture.md)
2. [Airflow DAG Development](../airflow/README.md#adding-new-dag)
3. [dbt Best Practices](../dbt/README.md#development-workflow)
4. [FastAPI Advanced Topics](../backend/README.md#adding-new-endpoint)

### Experiment

1. **Add more stocks**: Modify `TICKERS` in Airflow DAGs
2. **Modify indicators**: Add new dbt calculations
3. **Create visualizations**: Add charts to frontend
4. **Extend API**: Create new endpoints for analysis

### Deploy

1. **On-prem server**: SSH into server, clone repo, `docker compose up`
2. **Kubernetes**: Create Helm chart, deploy services
3. **Monitor**: Set up alerts, logging, dashboards

## Getting Help

1. **Check documentation**: Start with module READMEs
2. **Review architecture**: Read [System Architecture](architecture.md)
3. **Check logs**: `docker compose logs <service>`
4. **Database queries**: Connect to databases directly
5. **Code exploration**: Read source code (well-commented)

## Summary

You now understand:

✅ Foundation Flow architecture
✅ How to start all services locally
✅ How to ingest data from Yahoo Finance
✅ How to query raw and analytics data
✅ How to modify and deploy changes
✅ Where to find help and documentation

Happy analyzing! 📈
