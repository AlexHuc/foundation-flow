# Airflow Data Orchestration Layer

Apache Airflow orchestrates all batch ETL pipelines for Yahoo Finance data ingestion.

## Overview

Airflow handles:
- Batch scheduling (daily prices, weekly fundamentals)
- Retry logic and error handling
- Task dependencies and parallelization
- Monitoring and alerting
- Data quality checks

## Architecture

```
DAG: yahoo_fetch_daily_prices
  ├── Log DAG info
  ├── Fetch prices AAPL [parallel]
  ├── Fetch prices MSFT [parallel]
  ├── Fetch prices GOOGL [parallel]
  └── ... (other tickers)
  └── Verify data quality

DAG: yahoo_fetch_fundamentals (weekly)
  ├── Log DAG info
  ├── Fetch fundamentals AAPL [parallel]
  ├── Fetch fundamentals MSFT [parallel]
  └── ... (other tickers)
```

## Directory Structure

```
airflow/
├── dags/                       # Airflow DAG definitions
│   ├── yahoo_fetch_daily_prices.py
│   ├── yahoo_fetch_fundamentals.py
│   └── __init__.py
├── operators/                  # Custom operators
│   ├── yahoo_finance_operators.py
│   └── __init__.py
├── plugins/                    # Plugin configurations
│   └── __init__.py
└── README.md                   # This file
```

## DAGs

### 1. yahoo_fetch_daily_prices

**Purpose**: Fetch OHLCV (Open, High, Low, Close, Volume) prices from Yahoo Finance

**Schedule**: Daily at 11 PM UTC (6 PM ET, after market close)

**Idempotent**: Yes - can be safely rerun

**Configuration**:
```python
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NFLX', 'META', 'NVIDIA']
PERIOD = '1d'      # Fetch daily prices
INTERVAL = '1d'    # Daily bars
```

**Workflow**:
1. Log execution details
2. Fetch prices for each ticker (parallel)
3. Store in `raw.yahoo_prices_raw` table
4. Verify data quality

**Retry Policy**:
- Max retries: 3
- Retry delay: 5 minutes
- Exponential backoff: 2x multiplier

### 2. yahoo_fetch_fundamentals

**Purpose**: Fetch fundamental metrics (P/E, dividend yield, market cap, etc.)

**Schedule**: Weekly on Monday 8 AM UTC (3 AM ET)

**Idempotent**: Yes - overwrites previous snapshot

**Configuration**:
```python
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NFLX', 'META', 'NVIDIA']
```

**Metrics Fetched**:
- Market cap
- P/E ratio
- Dividend yield
- Earnings per share
- 52-week high/low
- Beta
- Average volume

**Workflow**:
1. Log execution details
2. Fetch fundamentals for each ticker (parallel)
3. Store in `raw.yahoo_fundamentals_raw` table

## Custom Operators

### YahooFinanceBaseOperator

Base class for all Yahoo Finance operators.

**Features**:
- PostgreSQL connection management
- Error handling and validation
- Logging
- Retry handling

**Usage**:
```python
from airflow.operators.python import PythonOperator
from yahoo_finance_operators import FetchYahooFinancePricesOperator

operator = FetchYahooFinancePricesOperator(
    task_id='fetch_aapl',
    ticker='AAPL',
    period='1d',
    interval='1d'
)
```

### FetchYahooFinancePricesOperator

Fetch OHLCV price data.

**Parameters**:
- `ticker`: Stock symbol
- `period`: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '5y')
- `interval`: Bar interval ('1m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
- `postgres_conn_id`: Airflow connection ID (default: 'postgres_raw')

**Output**: DataFrame with columns [Open, High, Low, Close, Volume, Adj Close]

**Storage**: `raw.yahoo_prices_raw` table (upserted for idempotency)

### FetchYahooFinanceFundamentalsOperator

Fetch fundamental metrics.

**Parameters**:
- `ticker`: Stock symbol
- `postgres_conn_id`: Airflow connection ID (default: 'postgres_raw')

**Storage**: `raw.yahoo_fundamentals_raw` table

## Data Storage

### Raw PostgreSQL Layer

All raw data is stored in PostgreSQL with schema `raw.`:

#### yahoo_prices_raw
```sql
CREATE TABLE raw.yahoo_prices_raw (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    date DATE,
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume BIGINT,
    adj_close NUMERIC(10, 2),
    raw_response JSONB,
    ingested_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### yahoo_fundamentals_raw
```sql
CREATE TABLE raw.yahoo_fundamentals_raw (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    market_cap BIGINT,
    pe_ratio NUMERIC(10, 2),
    dividend_yield NUMERIC(10, 4),
    earnings_per_share NUMERIC(10, 2),
    fifty_two_week_high NUMERIC(10, 2),
    fifty_two_week_low NUMERIC(10, 2),
    average_volume BIGINT,
    beta NUMERIC(5, 3),
    raw_response JSONB,
    ingested_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Configuration

### Airflow Connection Setup

Add PostgreSQL connection for raw data layer:

```bash
# Via Airflow UI
1. Admin → Connections
2. Create new connection:
   - Connection ID: postgres_raw
   - Connection Type: PostgreSQL
   - Host: postgres
   - Port: 5432
   - Schema: analytics
   - Login: airflow
   - Password: airflow
```

Or via Docker:
```bash
docker compose exec airflow-webserver airflow connections add postgres_raw \
    --conn-type postgres \
    --conn-host postgres \
    --conn-port 5432 \
    --conn-login airflow \
    --conn-password airflow \
    --conn-schema analytics
```

### Environment Variables

Set in `infrastructure/.env`:

```bash
AIRFLOW_HOME=/opt/airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/analytics
```

## Running Pipelines

### Access Airflow UI

```bash
# Start services
docker compose -f infrastructure/docker-compose.yml up -d

# Access UI
open http://localhost:8080

# Default credentials (in development)
# Check docker-compose.yml or Airflow initialization
```

### Trigger DAG Manually

```bash
# Via API
curl -X POST http://localhost:8080/api/experimental/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "dag_id": "yahoo_fetch_daily_prices",
    "conf": {"tickers": ["AAPL", "MSFT"]}
  }'

# Via CLI
docker compose exec airflow-webserver airflow dags trigger yahoo_fetch_daily_prices

# Via UI
1. Go to DAG list
2. Click DAG name
3. Click "Trigger DAG" button
```

### Monitor Execution

```bash
# View DAG runs
docker compose logs -f airflow-scheduler

# View specific task logs
docker compose exec airflow-webserver airflow tasks logs yahoo_fetch_daily_prices fetch_prices_AAPL <run_id>

# Check task status
docker compose exec airflow-webserver airflow tasks list yahoo_fetch_daily_prices
```

## Troubleshooting

### Scheduler Not Running

```bash
# Check scheduler logs
docker compose logs airflow-scheduler

# Restart scheduler
docker compose restart airflow-scheduler

# Verify database connectivity
docker compose exec airflow-scheduler airflow db check
```

### DAG Not Appearing

```bash
# Validate DAG syntax
docker compose exec airflow-webserver airflow dags validate

# List all DAGs
docker compose exec airflow-webserver airflow dags list

# Test specific DAG
docker compose exec airflow-webserver airflow dags test yahoo_fetch_daily_prices <date>
```

### Task Failures

```bash
# Check task logs
docker compose exec airflow-webserver airflow tasks logs <dag_id> <task_id> <run_id>

# Test task locally
docker compose exec airflow-webserver airflow tasks test <dag_id> <task_id> <date>

# Retry failed task
docker compose exec airflow-webserver airflow tasks clear <dag_id> -t <task_id>
```

### Yahoo Finance API Issues

- **Rate limits**: Yahoo Finance has rate limits. Default: 1-2 requests/second
- **Timeouts**: Increased from 30s to handle slow connections
- **Missing data**: Some tickers may have sparse data

## Development

### Adding New DAG

1. Create DAG file in `dags/`:
```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'data-engineering',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'my_dag',
    default_args=default_args,
    schedule_interval='0 9 * * 1',  # Weekly Monday 9 AM
    tags=['my-tag'],
)

# Add tasks...
```

2. Place file in `airflow/dags/` directory
3. Airflow will auto-discover within minutes

### Creating Custom Operator

1. Extend `BaseOperator`:
```python
from airflow.models import BaseOperator

class MyCustomOperator(BaseOperator):
    def __init__(self, param: str, **kwargs):
        super().__init__(**kwargs)
        self.param = param
    
    def execute(self, context):
        # Implementation
        return result
```

2. Place in `operators/` directory
3. Import in DAGs as needed

## Testing

### Unit Tests

```bash
# Run tests
cd airflow
python -m pytest tests/

# Test specific DAG
python -m pytest tests/test_yahoo_fetch_daily_prices.py
```

### DAG Validation

```bash
# Syntax validation
python -m py_compile dags/yahoo_fetch_daily_prices.py

# Airflow validation
docker compose exec airflow-webserver airflow dags validate
```

## Performance Tuning

### Parallelization

Increase parallel task execution in Airflow config:

```python
# airflow.cfg
parallelism = 32
dag_concurrency = 16
```

### Batch Size

Reduce or increase records processed per task based on memory:

```python
# In operators
BATCH_SIZE = 1000  # Adjust as needed
```

## Documentation

- [System Architecture](../docs/architecture.md)
- [Data Flow](../docs/data_flow.md)
- [dbt Transformation](../dbt/README.md)
- [Backend API](../backend/README.md)

## Related Files

- [Infrastructure Setup](../infrastructure/README.md)
- [Database Schema](../docs/schema_design.md)
