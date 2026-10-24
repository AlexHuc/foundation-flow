# FastAPI Backend

REST API for serving stock analytics data from PostgreSQL and TimescaleDB.

## Overview

The backend provides:
- Clean REST API with OpenAPI documentation
- Service layer for business logic
- Connection pooling for database efficiency
- Comprehensive error handling
- Data validation with Pydantic

## Architecture

```
Client (Frontend/External)
    ↓
FastAPI (REST API + OpenAPI docs)
    ↓
API Routers (stocks.py)
    ↓
Services (stock_service.py)
    ↓
Database Layer (PostgreSQL + TimescaleDB)
```

## Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   └── __init__.py
├── api/
│   ├── stocks.py            # Stock endpoints
│   └── __init__.py
├── services/
│   ├── stock_service.py     # Business logic
│   └── __init__.py
├── db/
│   ├── connection.py        # Database connection management
│   └── __init__.py
├── models/
│   ├── schemas.py           # Pydantic models
│   └── __init__.py
├── tests/
│   └── __init__.py
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## API Endpoints

### Health Check
- `GET /`: Basic health check
- `GET /health`: Detailed health check with database connectivity

### Stock Data
- `GET /api/stocks`: List all available stocks
- `GET /api/stocks/search?q=<query>`: Search for stocks
- `GET /api/stocks/{ticker}`: Get latest metrics for a stock
- `GET /api/stocks/{ticker}/prices`: Get historical prices
- `GET /api/stocks/{ticker}/returns`: Get return calculations

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 13+ (raw layer)
- TimescaleDB (analytics layer)

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export TIMESCALE_HOST=localhost
export LOG_LEVEL=INFO
```

## Running Locally

```bash
# Start databases first
docker compose -f infrastructure/docker-compose.yml up postgres timescale

# Run FastAPI development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access API
# Interactive docs: http://localhost:8000/docs
# Alternative docs: http://localhost:8000/redoc
```

## Configuration

Set environment variables in `infrastructure/.env`:

```bash
# Database Configuration
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=analytics
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

TIMESCALE_USER=postgres
TIMESCALE_PASSWORD=postgres
TIMESCALE_DB=analytics_prod
TIMESCALE_HOST=timescale
TIMESCALE_PORT=5433

# API Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_ENV=development
FASTAPI_DEBUG=True

LOG_LEVEL=INFO
```

## API Examples

### Get Stock Metrics

```bash
curl http://localhost:8000/api/stocks/AAPL
```

Response:
```json
{
  "ticker": "AAPL",
  "current_price": 186.50,
  "market_cap": 2900000000000,
  "pe_ratio": 28.5,
  "dividend_yield": 0.004,
  "beta": 1.2,
  "fifty_two_week_high": 199.62,
  "fifty_two_week_low": 124.17,
  "fifty_two_week_position_pct": 55.2,
  "annual_return": 0.487,
  "volatility_252d": 0.203,
  "updated_at": "2024-01-15T20:30:00Z"
}
```

### Get Historical Prices

```bash
curl "http://localhost:8000/api/stocks/AAPL/prices?days=30"
```

Response:
```json
[
  {
    "ticker": "AAPL",
    "date": "2024-01-15",
    "open": 185.50,
    "high": 186.75,
    "low": 185.25,
    "close": 186.50,
    "volume": 45000000,
    "adj_close": 186.50,
    "daily_return": 0.0027,
    "volatility_20d": 0.156,
    "volatility_252d": 0.203
  }
]
```

### Search Stocks

```bash
curl "http://localhost:8000/api/stocks/search?q=APP"
```

Response:
```json
["AAPL", "APPF", "APPN"]
```

## Code Structure

### Main Application (app/main.py)

Entry point for FastAPI:
- Initializes app with CORS middleware
- Includes routers for API endpoints
- Configures lifespan events (startup/shutdown)
- Provides health check endpoints

### API Routes (api/stocks.py)

REST endpoint definitions:
- Request validation with Query parameters
- Response serialization with Pydantic models
- Comprehensive docstrings for OpenAPI
- Error handling with HTTPExceptions

### Services (services/stock_service.py)

Business logic layer:
- Queries analytics layer
- Data transformation
- Caching strategies (future)
- Error handling and logging

### Database (db/connection.py)

Connection management:
- Connection pooling (asyncpg)
- Separate pools for raw and analytics databases
- Error handling and logging
- Graceful shutdown

### Models (models/schemas.py)

Pydantic data models:
- Request/response validation
- JSON serialization
- OpenAPI schema generation
- Example data for documentation

## Development Workflow

### Adding New Endpoint

1. **Define schema** in `models/schemas.py`:
```python
class MyData(BaseModel):
    field: str = Field(..., description="Field description")
```

2. **Create service function** in `services/stock_service.py`:
```python
async def get_my_data(param: str):
    conn = await get_analytics_connection()
    result = await conn.fetch("SELECT ...")
    await conn.close()
    return result
```

3. **Add route** in `api/stocks.py`:
```python
@router.get("/endpoint", response_model=MyData)
async def my_endpoint(param: str):
    data = await get_my_data(param)
    return data
```

### Testing

```bash
# Run specific endpoint
curl http://localhost:8000/api/stocks/AAPL

# Check OpenAPI documentation
curl http://localhost:8000/docs

# View API schema
curl http://localhost:8000/openapi.json
```

## Performance

### Connection Pooling
- Pool size: 5-20 connections per database
- Reuses connections for efficiency
- Handles concurrent requests

### Query Optimization
- Uses indexes on frequently queried columns
- Limits result sets (500 records max)
- Efficient joins in TimescaleDB

### Caching (Future)
- Redis for frequently accessed metrics
- Cache invalidation on data updates

## Monitoring

### Logging

All operations are logged:

```python
logger.info(f"Fetched {len(prices)} price records for {ticker}")
logger.error(f"Error fetching stock {ticker}: {str(e)}")
```

### Health Checks

```bash
# Basic health
curl http://localhost:8000/

# Detailed with database checks
curl http://localhost:8000/health
```

## Error Handling

All errors return standard format:

```json
{
  "detail": "Error message",
  "status_code": 404
}
```

Common status codes:
- 200: Success
- 400: Bad request (invalid parameters)
- 404: Resource not found
- 500: Server error (database issues)
- 503: Service unavailable (database down)

## Troubleshooting

### "Database connection failed"

```bash
# Check database connectivity
psql -h localhost -U airflow -d analytics

# View logs
docker compose logs backend
```

### "Stock not found"

- Verify stock ticker in analytics database:
  ```sql
  SELECT DISTINCT ticker FROM marts.fact_stock_metrics LIMIT 10;
  ```
- Ensure Airflow pipelines have run and dbt transformations completed

### "Slow API responses"

- Check database query performance:
  ```sql
  EXPLAIN ANALYZE SELECT * FROM marts.fact_stock_prices;
  ```
- Monitor connection pool usage:
  ```bash
  docker compose logs backend | grep "pool"
  ```

## Documentation

- [System Architecture](../docs/architecture.md)
- [Database Schema](../docs/schema_design.md)
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://spec.openapis.org/)

## Related Components

- [Airflow DAGs](../airflow/README.md)
- [dbt Transformations](../dbt/README.md)
- [Next.js Frontend](../frontend/README.md)
- [Infrastructure Setup](../infrastructure/README.md)
