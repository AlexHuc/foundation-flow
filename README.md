# Foundation Flow

> **Discover your Ego. Enter the Flow State.**

**Foundation Flow** is a self-hosted, batch-oriented financial data platform for researching publicly traded companies. Its current focus is ingesting and retaining Yahoo Finance data in PostgreSQL using Apache Airflow. The longer-term goal is to transform those datasets into reusable analytics and expose them through a secure API and a premium stock-analysis web application.

> **Project status:** The Docker-based data platform, Yahoo Finance ingestion operators, the **FastAPI backend** (`backend/`), and the **TanStack Start frontend** (`frontend/`) are all running services in the Docker Compose configuration documented here. TimescaleDB and dbt are available as infrastructure, but their presence alone does not imply that analytical models, hypertables, or marts have been built.

## Architecture

```mermaid
flowchart LR
    YF[Yahoo Finance / yfinance] --> AF[Apache Airflow<br/>Scheduler + DAG Processor + API Server]
    AF --> PG[(PostgreSQL 15<br/>Landing data)]
    PGA[pgAdmin] -. Administration .-> PG
    PGA -. Administration .-> TS
    PG -. Planned / model-dependent transformations .-> DBT[dbt CLI]
    DBT -. Planned / model-dependent outputs .-> TS[(TimescaleDB<br/>PostgreSQL 15)]
    PG -- Read-only SELECT --> API[FastAPI REST API]
    TS -. Future analytics access .-> API
    API -- JSON over HTTP --> WEB[TanStack Start + React<br/>TypeScript + Tailwind]
```

**Solid arrows** show the ingestion and serving flow already represented by the project. **Dashed arrows** show administration, optional transformations, or planned analytics integration; they are not claims that those data flows are already operational.

### Current vs. planned components

| Component | Technology | Status | Purpose |
|---|---|---|---|
| Market data source | Yahoo Finance via `yfinance` | Current | Public-company market, fundamentals, estimates, ownership, options, and filings data |
| Ingestion / orchestration | Apache Airflow with custom operators | Current | Scheduled, retryable batch ingestion |
| Landing database | PostgreSQL 15 Alpine | Current | Store Yahoo Finance records in the `landing` schema |
| Analytics database | TimescaleDB (PostgreSQL 15-compatible image) | Provisioned | Intended time-series / analytics storage |
| Database administration | pgAdmin 4 | Current | Inspect and administer both databases |
| Transformation tooling | dbt | Provisioned, optional profile | Transform landing data as models are implemented |
| Backend | FastAPI + asyncpg | Current | Read-only REST API over the `landing` schema, with OpenAPI docs |
| Frontend | TanStack Start (React 19), TypeScript, Tailwind CSS | Current | Fundamental research dashboard |

## Current Docker Compose services

The Compose file is located at **`infrastructure/docker-compose.yml`**.

| Service | Container | Image / build | Host access |
|---|---|---|---|
| `postgres` | `foundation_postgres` | `postgres:15-alpine` | `${POSTGRES_PORT}` → 5432 |
| `timescale` | `foundation_timescale` | `timescale/timescaledb:latest-pg15-oss` | `${TIMESCALE_PORT}` → 5432 |
| `pgadmin` | `foundation_pgadmin` | `dpage/pgadmin4:latest` | `127.0.0.1:${PGADMIN_PORT}` → 80 |
| `airflow-scheduler` | `foundation_airflow_scheduler` | `docker/Dockerfile.airflow` | Internal |
| `airflow-dag-processor` | `foundation_airflow_dag_processor` | `docker/Dockerfile.airflow` | Internal |
| `airflow-webserver` | `foundation_airflow_webserver` | `docker/Dockerfile.airflow` | `${AIRFLOW_WEBSERVER_PORT}` → 8080 |
| `backend` | `foundation_backend` | `docker/Dockerfile.backend` (context: repo root) | `${BACKEND_PORT:-8000}` → 8000 |
| `frontend` | `foundation_frontend` | `docker/Dockerfile.frontend` (context: repo root) | `${FRONTEND_PORT:-3000}` → 3000 |
| `dbt` | `foundation_dbt` | `docker/Dockerfile.dbt` | CLI; profile `tools` |

**Airflow naming note:** The service is named `airflow-webserver` for compatibility with the project, but its actual command is **`airflow api-server`**. The DAG processor runs separately using **`airflow dag-processor`**, and the scheduler starts with **`airflow db migrate && airflow scheduler`**. Do not assume an older Airflow 2.x webserver or experimental API layout.

All services share the Docker network `foundation`. The data and log volumes are:

- `postgres_data` — PostgreSQL persistence
- `timescale_data` — TimescaleDB persistence
- `pgadmin_data` — pgAdmin configuration
- `airflow_logs` — Airflow logs

The `dbt` service is in the `tools` profile, so it does **not** start with the default `docker compose up -d` command.

## Repository layout

The paths below document the current data-platform structure and the **planned** application modules. They are not a claim that every example file already exists.

```text
foundation-flow/
├── README.md
├── airflow/
│   ├── dags/
│   │   └── yahoo_finance/             # Dataset-specific ingestion DAGs
│   ├── operators/
│   │   └── yahoo_finance/             # Base operator + custom fetch operators
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── major_holders.py
│   │       ├── institutional_holders.py
│   │       ├── mutualfund_holders.py
│   │       ├── insider_transactions.py
│   │       ├── insider_purchases.py
│   │       ├── insider_roster_holders.py
│   │       └── sec_filings.py
│   └── plugins/
├── database/
│   └── migrations/postgres/landing/yfinance/
│       └── ...                       # Landing-table SQL migrations
├── dbt/                              # dbt project / transformations
├── infrastructure/
│   ├── docker-compose.yml
│   ├── docker/
│   │   ├── Dockerfile.airflow
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── Dockerfile.dbt
│   ├── scripts/
│   │   ├── init_postgres.sql
│   │   └── init_timescale.sql
│   └── dbt/
│       └── profiles.yml             # Mounted into the dbt container
├── backend/                          # FastAPI application (read-only API over `landing`)
│   ├── app/
│   │   ├── main.py                   # FastAPI app, CORS, /api/health
│   │   ├── config.py                 # Environment-based settings
│   │   ├── db.py                     # asyncpg pool, read-only sessions
│   │   ├── registry.py               # Whitelisted dataset → table/column mapping
│   │   ├── serialization.py          # JSON-safe rows (NUMERIC, dates, big numbers)
│   │   └── routes/                   # companies, datasets, pipelines
│   └── requirements.txt
└── frontend/                         # TanStack Start application
    ├── src/lib/api.ts                # Data layer: real-data mode vs. demo mode
    ├── src/routes/                   # Landing page + research workspace
    └── ...                           # Vite / Tailwind / React Query setup
```

## Yahoo Finance ingestion coverage

The custom operators fetch datasets from `yf.Ticker(ticker)` and write them to the PostgreSQL landing layer. The underlying implementation uses normalized column names, PostgreSQL schema discovery, and upserts where appropriate.

The following catalog reflects the ingestion pipelines developed for the project. **Run the schema checks below to confirm which tables and rows are actually present in your running database.**

| Area | Dataset | Expected landing table |
|---|---|---|
| Market data | Historical prices (`history`) | Check actual migration / schema |
| Company data | Company information (`info`) | Check actual migration / schema |
| Company data | Fast information (`fast_info`) | Check actual migration / schema |
| Financials | Annual income statement | `landing.yahoo_income_statement` |
| Financials | Quarterly income statement | `landing.yahoo_quarterly_income_statement` |
| Financials | TTM income statement | `landing.yahoo_ttm_income_statement` |
| Financials | Annual balance sheet | `landing.yahoo_balance_sheet` |
| Financials | Quarterly balance sheet | `landing.yahoo_quarterly_balance_sheet` |
| Financials | Annual cash flow | `landing.yahoo_cashflow` |
| Financials | Quarterly cash flow | `landing.yahoo_quarterly_cashflow` |
| Financials | TTM cash flow | `landing.yahoo_ttm_cashflow` |
| Earnings | Earnings dates | `landing.yahoo_earnings_dates` |
| Earnings | Calendar | `landing.yahoo_calendar` |
| Earnings | Earnings history | `landing.yahoo_earnings_history` |
| Estimates | Earnings estimates | `landing.yahoo_earnings_estimate` |
| Estimates | Revenue estimates | `landing.yahoo_revenue_estimate` |
| Estimates | EPS trend | `landing.yahoo_eps_trend` |
| Estimates | EPS revisions | `landing.yahoo_eps_revisions` |
| Estimates | Growth estimates | `landing.yahoo_growth_estimates` |
| Analysts | Recommendations | `landing.yahoo_recommendations` |
| Analysts | Upgrades / downgrades | `landing.yahoo_upgrades_downgrades` |
| Derivatives | Options chain | `landing.yahoo_option_chain` |
| Ownership | Major holders | `landing.yahoo_major_holders` |
| Ownership | Institutional holders | `landing.yahoo_institutional_holders` |
| Ownership | Mutual fund holders | `landing.yahoo_mutualfund_holders` |
| Insider activity | Insider transactions | `landing.yahoo_insider_transactions` |
| Insider activity | Insider purchases | `landing.yahoo_insider_purchases` |
| Insider activity | Insider roster | `landing.yahoo_insider_roster_holders` |
| Filings | SEC filings | `landing.yahoo_sec_filings` |

**Data model conventions:**

- Many ownership, analyst, options, and filing tables have a `date` **UTC ingestion snapshot** column.
- Financial statements have fiscal reporting periods; do not interpret every `date` column as an ingestion date.
- Holder records also contain `date_reported`; insider transactions contain `start_date`; options contain `expiration`; filings contain `filing_date`.
- Analyst relative periods such as `0q`, `+1q`, and `0m` need a snapshot date for correct interpretation.
- Percentages are often stored as **decimal fractions** (for example, `0.01655` = 1.655%). Verify field-specific units before presenting them.
- SEC exhibit URLs are stored as `JSONB` where the corresponding migration has been applied.
- Landing tables preserve source observations; they are not automatically production-ready dimensional marts.

## Quick start

### Prerequisites

- Docker Engine and Docker Compose plugin
- Docker access for your local user
- An environment file with the variables used by the Compose configuration
- Network access for the `yfinance` ingestion tasks

### 1. Configure environment variables

From the repository root:

```bash
cd infrastructure
# If an example file is present, copy it and edit the values:
cp env.example .env
```

If `env.example` is not present, create `infrastructure/.env` yourself using the variables referenced in `docker-compose.yml`.

Important environment variables include:

| Group | Variables |
|---|---|
| PostgreSQL | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` |
| TimescaleDB | `TIMESCALE_USER`, `TIMESCALE_PASSWORD`, `TIMESCALE_DB`, `TIMESCALE_PORT` |
| pgAdmin | `PGADMIN_EMAIL`, `PGADMIN_PASSWORD`, `PGADMIN_PORT` |
| Airflow | `AIRFLOW_WEBSERVER_PORT`, `AIRFLOW_HOME`, `AIRFLOW_UID`, `AIRFLOW_GID`, `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`, and the other `AIRFLOW__...` settings in Compose |
| dbt | `DBT_POSTGRES_HOST`, `DBT_TIMESCALE_HOST` (and the database credentials above) |
| Backend | `BACKEND_PORT`, `CORS_ORIGINS`, optional `BACKEND_DATABASE_URL` |
| Frontend | `FRONTEND_PORT`, `VITE_API_BASE_URL` |

The database hosts **inside Docker** are typically `postgres` and `timescale`, on container port `5432`. Host-mapped ports are for clients running outside the Docker network.

Use strong secrets; do not commit `.env` or real credentials to Git. Confirm that the Airflow connection ID **`postgres_landing`** points to the intended PostgreSQL database.

### 2. Start the current platform

Run from the `infrastructure/` directory:

```bash
docker compose config --services
docker compose up -d --build
docker compose ps
```

The standard startup includes PostgreSQL, TimescaleDB, pgAdmin, the Airflow scheduler, the Airflow DAG processor, the Airflow API server, the FastAPI backend, and the TanStack Start frontend. The `dbt` CLI service is optional and started on demand.

The `backend` service waits for PostgreSQL to report healthy, connects to it at the Docker hostname `postgres:5432` (never `localhost`), and serves Uvicorn on port 8000. The `frontend` service builds the TanStack Start app with `VITE_API_BASE_URL` baked in for browser requests (default `http://localhost:8000`) and uses the runtime `API_INTERNAL_URL=http://backend:8000` for server-side rendering fetches inside the Docker network.

### 3. Open the available interfaces

| Interface | Address |
|---|---|
| Frontend (TanStack Start) | `http://localhost:<FRONTEND_PORT>` (default 3000) |
| FastAPI backend | `http://localhost:<BACKEND_PORT>` (default 8000) |
| API documentation (OpenAPI) | `http://localhost:<BACKEND_PORT>/docs` |
| API health check | `http://localhost:<BACKEND_PORT>/api/health` |
| Airflow API server / UI | `http://localhost:<AIRFLOW_WEBSERVER_PORT>` |
| pgAdmin | `http://127.0.0.1:<PGADMIN_PORT>` |
| PostgreSQL TCP | `localhost:<POSTGRES_PORT>` |
| TimescaleDB TCP | `localhost:<TIMESCALE_PORT>` |

Replace angle-bracket placeholders with values from `.env`.

In pgAdmin, register the database servers using Docker service names and port `5432`:

- PostgreSQL: host `postgres`
- TimescaleDB: host `timescale`

### 3a. Verify the application stack

After `docker compose up -d --build`, verify each layer in order:

```bash
# 1. Compose configuration is valid and lists every service
docker compose config --services

# 2. All services are up and healthy
docker compose ps

# 3. PostgreSQL is healthy and holds the landing schema
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT count(*) FROM landing.yahoo_history;"

# 4. The API health check verifies database connectivity (HTTP 200 = DB up)
curl -i http://localhost:8000/api/health

# 5. Real company records from the landing schema
curl http://localhost:8000/api/companies

# 6. Historical prices for CRDO (once ingestion has run)
curl "http://localhost:8000/api/companies/CRDO/prices?limit=5"

# 7. Populated financial datasets
curl "http://localhost:8000/api/companies/CRDO/financials/income?period=annual"

# 8. The frontend serves and its SSR fetches reach the backend
curl -I http://localhost:3000/
```

Then open `http://localhost:3000`, search for `CRDO` in the top navigation, and open `/company/CRDO`. With the API reachable, every data label reads **Reported** (or **Calculated** for derived metrics) and values come from your database. Empty datasets render explicit empty states; missing metrics render as `—`.

**Real-data mode vs. demo mode.** The frontend decides at build time: with `VITE_API_BASE_URL` set (the Docker default), it is in *real-data mode* — if the backend is unreachable, pages show a **Connection Error** with a retry button and never substitute sample numbers. With `VITE_API_BASE_URL` unset (e.g. `bun run dev` without env), the frontend runs in *demo mode* with clearly labeled **Illustrative** sample data for design exploration.

### 3b. Container logs and stopping the stack

```bash
# Follow backend or frontend logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop everything, KEEPING database volumes and ingested data
docker compose down

# Danger: also deletes postgres_data / timescale_data volumes
# docker compose down -v
```

### 3c. Read-only database role (optional but recommended)

The API only ever runs `SELECT` queries and enforces `default_transaction_read_only=on` at the session level. For defense in depth, create a dedicated SELECT-only role and point the backend at it:

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
CREATE ROLE foundation_ro LOGIN PASSWORD 'choose_a_strong_password';
GRANT USAGE ON SCHEMA landing TO foundation_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA landing TO foundation_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA landing GRANT SELECT ON TABLES TO foundation_ro;
SQL
```

Then set `BACKEND_DATABASE_URL=postgresql://foundation_ro:choose_a_strong_password@postgres:5432/<POSTGRES_DB>` in `infrastructure/.env` and rebuild the backend service.

### 4. Inspect the Airflow DAGs

```bash
docker compose exec airflow-dag-processor airflow dags list
docker compose exec airflow-dag-processor airflow dags list-import-errors
```

To verify a custom operator imports:

```bash
docker compose exec airflow-dag-processor \
  python -c "from operators.yahoo_finance import FetchYahooFinanceSECFilings; print('Import successful')"
```

Trigger ingestion DAGs using your Airflow UI or the API version supported by the installed Airflow image. Do **not** use the legacy `/api/experimental/...` endpoints from the old README.

### 5. Check the landing tables

List existing Yahoo Finance tables in PostgreSQL:

```bash
docker compose exec postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT table_name FROM information_schema.tables WHERE table_schema = '\''landing'\'' AND table_name LIKE '\''yahoo_%'\'' ORDER BY table_name;"'
```

Or run the following SQL using pgAdmin:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'landing'
  AND table_name LIKE 'yahoo_%'
ORDER BY table_name;
```

Inspect a table's columns:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'landing'
  AND table_name = 'yahoo_sec_filings'
ORDER BY ordinal_position;
```

Check a recent SEC filings snapshot, if the migration and ingestion have completed:

```sql
SELECT ticker, date, filing_date, type, title, edgar_url
FROM landing.yahoo_sec_filings
WHERE ticker = 'CRDO'
ORDER BY date DESC, filing_date DESC
LIMIT 20;
```

### 6. Run dbt when needed

`dbt` is defined under the Compose profile **`tools`** and is configured with both PostgreSQL and TimescaleDB connection variables.

```bash
# Verify the configured dbt connection and project.
docker compose --profile tools run --rm --entrypoint dbt dbt debug

# When dbt models are available:
docker compose --profile tools run --rm --entrypoint dbt dbt run
docker compose --profile tools run --rm --entrypoint dbt dbt test
```

The dbt project is mounted from `../dbt` into `/usr/app/dbt`; its profile is mounted from `./dbt/profiles.yml` in the infrastructure directory to `/root/.dbt/profiles.yml`.

Running dbt successfully depends on the models, profile targets, and destination schemas actually configured in the repository.

## Migrations and database initialization

The Compose services mount:

- `infrastructure/scripts/init_postgres.sql` into the PostgreSQL initialization directory.
- `infrastructure/scripts/init_timescale.sql` into the TimescaleDB initialization directory.

**Important:** Docker's `/docker-entrypoint-initdb.d` scripts run only when the relevant database data directory is first initialized. Restarting a container with an existing volume **does not re-run** those scripts.

Landing table migrations under `database/migrations/postgres/landing/yfinance/` must be applied to the correct PostgreSQL database using your migration workflow. Merely creating a new SQL migration file does not create the table.

For example, from `infrastructure/`, to apply the SEC filings migration manually:

```bash
docker compose exec -T postgres sh -c \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < ../database/migrations/postgres/landing/yfinance/029_sec_filings.sql
```

Apply migrations in the required order and verify the resulting schema before triggering the corresponding DAG.

**Do not run `docker compose down -v` casually:** it removes named volumes and can permanently delete local database data and Airflow logs.

## Troubleshooting

### Airflow cannot find a landing table

If a task logs an error such as `Table landing.yahoo_sec_filings does not exist or has no columns`:

1. Confirm that the migration was executed, not merely saved to disk.
2. Check that it was applied to the database referenced by `postgres_landing`.
3. Confirm the schema is `landing`, not `public`.
4. Verify that the Airflow database user has permission to inspect the table.
5. Query `information_schema.columns` or `to_regclass('landing.yahoo_sec_filings')` using the **same connection Airflow uses**.

Example, from `infrastructure/`:

```bash
docker compose exec -T airflow-dag-processor python - <<'PY'
from airflow.providers.postgres.hooks.postgres import PostgresHook

hook = PostgresHook(postgres_conn_id="postgres_landing")
row = hook.get_first(
    "SELECT current_database(), current_user, "
    "to_regclass('landing.yahoo_sec_filings')"
)
print("Database:", row[0])
print("User:", row[1])
print("Table:", row[2])
PY
```

If `Table` prints `None`, the connected database cannot resolve the relation.

### Airflow DAG import errors

```bash
docker compose logs --tail=100 airflow-dag-processor
docker compose exec airflow-dag-processor airflow dags list-import-errors
```

Check module names, the `airflow/operators/yahoo_finance/__init__.py` exports, and mounted folders.

### Airflow services fail to start

```bash
docker compose ps
docker compose logs --tail=150 postgres airflow-scheduler airflow-dag-processor airflow-webserver
```

Check database health, environment variables, Airflow migrations, and shared credentials.

### dbt cannot connect

Verify that the profile points to `postgres` or `timescale` on Docker-network port `5432`, not a host-published port, and that the requested target database and schema exist.

### The frontend shows "Connection Error"

The frontend is in real-data mode and cannot reach the API. Check in order:

1. `docker compose ps` — is `foundation_backend` up and healthy?
2. `docker compose logs backend` — database connection errors mean PostgreSQL is unreachable or credentials are wrong; the backend retries and `/api/health` returns 503 until it connects.
3. `curl http://localhost:8000/api/health` from the host — if this fails, the backend container or port mapping is the problem.
4. If the health check passes but the browser still fails, the frontend image was built with a `VITE_API_BASE_URL` your browser cannot reach (for example the Docker-internal hostname `backend`). Set `VITE_API_BASE_URL=http://localhost:8000` in `infrastructure/.env` and rebuild: `docker compose up -d --build frontend`.
5. CORS errors in the browser console mean the frontend origin is missing from `CORS_ORIGINS` (default `http://localhost:3000`).

### Running the test suites

```bash
# Backend: exercised against a scratch PostgreSQL loaded with the landing migrations
cd backend && pip install -r requirements.txt

# Frontend: unit and mapping tests (13 tests)
cd frontend && bun install && bun run test
```

## Development roadmap

### Current focus — data ingestion and foundation

- Maintain the Docker-based services.
- Extend and operate Yahoo Finance ingestion DAGs and custom operators.
- Apply and track landing schema migrations.
- Validate data quality, scheduling, and historical/snapshot semantics.
- Define dbt staging, intermediate, and mart models as required.
- Decide which analytics should be materialized in TimescaleDB versus queried from PostgreSQL.

### Planned — analytics and transformation

- dbt staging and curated financial models.
- Financial metric definitions with consistent periods and units.
- Optimized time-series analytics and historical comparisons.
- Data freshness, validation, and lineage monitoring.

### Current — backend API

- FastAPI service with read-only access to financial data (`backend/`).
- Typed responses and parameterized queries.
- Company profiles, price history, statements, estimates, ownership, options, and filings endpoints.
- OpenAPI documentation at `/docs`; health check with database connectivity at `/api/health`.
- Still planned: caching, pagination, authentication.

### Current — frontend application

- TanStack Start / TypeScript / Tailwind CSS research dashboard (`frontend/`).
- Fundamental analysis, financial statements, and charts.
- Analyst, institutional ownership, insider activity, options, and SEC filings views (populated as datasets land).
- Premium dark Foundation Flow design system.
- Still planned: valuation tools, company comparisons, and watchlists backed by real data.

### Planned — production operations

- Authentication and authorization.
- TLS and restricted service exposure.
- Automated database backups and restore procedures.
- Monitoring, alerting, and ingestion observability.
- CI/CD, deployment automation, and secrets management.

## Operational and security notes

- **Batch data, not live quotes:** Yahoo Finance data ingested by scheduled Airflow jobs must be presented with its actual observation or snapshot date.
- **External access:** `postgres`, `timescale`, and the Airflow API server use host-published ports in the supplied Compose configuration. Restrict these ports with appropriate host/network controls if the machine is reachable by other users.
- **pgAdmin exposure:** The supplied Compose configuration binds pgAdmin to `127.0.0.1`, so it is accessible from the Docker host rather than automatically exposed on all interfaces.
- **Version pinning:** Several images use `latest` tags. Pin tested versions or digests before a production deployment to make upgrades predictable.
- **Data licensing:** Review Yahoo Finance terms and any data usage or redistribution restrictions before exposing sourced data through a public or commercial product.
- **Backups:** Named Docker volumes provide persistence, not a substitute for backup and restore testing.

---

**Foundation Flow** — *Discover your Ego. Enter the Flow State.*
