# Infrastructure Layer

Complete Docker-based deployment for Foundation Flow.

## Overview

This directory contains all infrastructure setup including:
- Docker Compose orchestration
- Database initialization scripts
- Service Dockerfiles
- Environment configuration

## Directory Structure

```
infrastructure/
├── docker/                     # Dockerfiles for all services
│   ├── Dockerfile.airflow
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── scripts/                    # Database initialization scripts
│   ├── init_postgres.sql       # PostgreSQL raw layer schema
│   └── init_timescale.sql      # TimescaleDB analytics layer schema
├── docker-compose.yml          # Full stack orchestration
├── env.example                 # Environment variable template
└── README.md                   # This file
```

## Services

### PostgreSQL (Port 5432)
- **Purpose**: Raw data ingestion layer
- **User**: airflow
- **Database**: analytics
- **Initialization**: Loads raw.* schema with Yahoo prices, fundamentals tables

### TimescaleDB (Port 5433)
- **Purpose**: Time-series optimized analytics layer
- **User**: postgres
- **Database**: analytics_prod
- **Features**: Hypertables, compression, continuous aggregates
- **Initialization**: Loads analytics.* schema with hypertables for stock prices

### Airflow (Port 8080)
- **Purpose**: Batch orchestration and scheduling
- **Scheduler**: Runs in separate container
- **Webserver**: UI for monitoring and triggering DAGs
- **Executor**: LocalExecutor (suitable for on-prem batch)

### FastAPI Backend (Port 8000)
- **Purpose**: REST API for data serving
- **Health Check**: GET /docs (OpenAPI documentation)
- **Dependencies**: PostgreSQL, TimescaleDB

### Next.js Frontend (Port 3000)
- **Purpose**: Stock dashboard and visualization
- **Health Check**: GET / (homepage)
- **Dependencies**: FastAPI backend

## Quick Start

### Prerequisites

```bash
# Check Docker installation
docker --version
docker compose version

# Minimum versions:
# - Docker: 20.10+
# - Docker Compose: 2.0+
```

### Starting the Stack

```bash
# 1. Clone repository
git clone <repo-url>
cd foundation-flow

# 2. Copy environment file
cp infrastructure/env.example infrastructure/.env

# 3. Start all services (from foundation-flow root)
docker compose -f infrastructure/docker-compose.yml up -d

# 4. Wait for services to initialize (2-3 minutes)
docker compose -f infrastructure/docker-compose.yml logs -f

# 5. Monitor healthchecks
docker compose -f infrastructure/docker-compose.yml ps
```

## Service Endpoints

Once running, access services at:

| Service | URL | Purpose |
|---------|-----|---------|
| Airflow UI | http://localhost:8080 | Monitor DAGs, trigger jobs |
| FastAPI Docs | http://localhost:8000/docs | Interactive API documentation |
| FastAPI ReDoc | http://localhost:8000/redoc | Alternative API docs |
| Frontend | http://localhost:3000 | Stock dashboard |

## Database Connections

### PostgreSQL (Raw Layer)

```bash
# Using psql from host
psql -h localhost -U airflow -d analytics -p 5432

# From inside container
docker compose exec postgres psql -U airflow -d analytics
```

### TimescaleDB (Analytics Layer)

```bash
# Using psql from host
psql -h localhost -U postgres -d analytics_prod -p 5433

# From inside container
docker compose exec timescale psql -U postgres -d analytics_prod
```

### Sample Queries

```sql
-- Check raw data ingestion
SELECT ticker, COUNT(*) as price_count 
FROM raw.yahoo_prices_raw 
GROUP BY ticker;

-- Check analytics hypertables
SELECT * FROM analytics.stock_prices 
WHERE ticker = 'AAPL' 
ORDER BY time DESC LIMIT 10;

-- Check moving averages
SELECT * FROM analytics.moving_averages 
WHERE ticker = 'AAPL' 
ORDER BY time DESC LIMIT 5;
```

## Environment Configuration

Edit `infrastructure/.env` to customize:

```bash
# Database credentials
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=analytics

# Airflow configuration
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False

# API configuration
FASTAPI_ENV=development
FASTAPI_DEBUG=True

# Frontend configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

## Logs and Debugging

### View Service Logs

```bash
# All services
docker compose -f infrastructure/docker-compose.yml logs -f

# Specific service
docker compose -f infrastructure/docker-compose.yml logs -f airflow-scheduler
docker compose -f infrastructure/docker-compose.yml logs -f backend

# Last 100 lines
docker compose -f infrastructure/docker-compose.yml logs --tail=100 airflow-webserver
```

### Stop Services

```bash
# Graceful shutdown
docker compose -f infrastructure/docker-compose.yml down

# Remove volumes (WARNING: deletes data)
docker compose -f infrastructure/docker-compose.yml down -v
```

### Restart Services

```bash
# Restart all
docker compose -f infrastructure/docker-compose.yml restart

# Restart specific service
docker compose -f infrastructure/docker-compose.yml restart backend
```

## Common Issues

### Port Already in Use

If a port is already taken:

```bash
# Find process using port (macOS/Linux)
lsof -i :5432
lsof -i :8080

# Kill process (replace PID)
kill -9 <PID>

# Or use different ports in .env
POSTGRES_PORT=5433
AIRFLOW_PORT=8081
```

### Database Connection Errors

```bash
# Check database health
docker compose exec postgres pg_isready
docker compose exec timescale pg_isready

# Verify network
docker compose exec postgres ping timescale
```

### Airflow Not Initializing

```bash
# Reinitialize Airflow database
docker compose exec airflow-webserver airflow db reset --yes
docker compose exec airflow-webserver airflow db init
```

## Development Workflow

### Running Locally Without Docker

For faster iteration during development:

```bash
# 1. Start only databases
docker compose -f infrastructure/docker-compose.yml up -d postgres timescale

# 2. Run backend locally
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# 3. Run frontend locally (in another terminal)
cd frontend
npm install
npm run dev
```

### Building Custom Images

```bash
# Rebuild all images
docker compose -f infrastructure/docker-compose.yml build

# Rebuild specific service
docker compose build backend

# Rebuild without cache
docker compose build --no-cache backend
```

## Monitoring

### Health Checks

All services include health checks:

```bash
# Check health status
docker compose -f infrastructure/docker-compose.yml ps

# Manual health check
curl http://localhost:8080/health      # Airflow
curl http://localhost:8000/docs        # FastAPI
curl http://localhost:3000             # Next.js
```

### Resource Usage

```bash
# Monitor container stats
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune
```

## Production Considerations

### NOT FOR PRODUCTION

This setup is designed for:
- Local development
- Testing
- Small-scale on-prem deployments

For production, consider:
- Kubernetes orchestration
- External database services
- Load balancing
- Data backup strategy
- SSL/TLS certificates
- Monitoring and alerting
- Security hardening

## Documentation

- [System Architecture](../docs/architecture.md)
- [Backend Setup](../backend/README.md)
- [Frontend Setup](../frontend/README.md)
- [Airflow Configuration](../airflow/README.md)
- [Database Schema](../docs/schema_design.md)
