# PostgreSQL Access Guide

## Connect to PostgreSQL

To open an interactive PostgreSQL session inside the Docker container:

```bash
docker exec -it foundation_postgres psql -U airflow -d analytics
```

### What this command does

| Part                | Meaning                                      |
|---------------------|----------------------------------------------|
| docker exec         | Execute a command inside a running container |
| -it                 | Open an interactive terminal                 |
| foundation_postgres | Container name                               |
| psql                | PostgreSQL command-line client               |
| -U airflow          | Connect as user `airflow`                    |
| -d analytics        | Connect to database `analytics`              |

---

## Useful PostgreSQL Commands

### List all databases

```sql
\l
```

Example output:

```text
analytics
postgres
template0
template1
```

---

### Connect to another database

```sql
\c postgres
```

---

### Show all tables

```sql
\dt
```

---

### Show all schemas

```sql
\dn
```

---

### Describe a table structure

```sql
\d table_name
```

Example:

```sql
\d stock_prices
```

Shows:

- columns
- data types
- indexes
- constraints

---

### View table data

```sql
SELECT * FROM stock_prices LIMIT 10;
```

---

### Count rows

```sql
SELECT COUNT(*) FROM stock_prices;
```

---

### Show currently connected database

```sql
SELECT current_database();
```

---

### Show current user

```sql
SELECT current_user;
```

---

### List users/roles

```sql
\du
```

---

### Show active connections

```sql
SELECT * FROM pg_stat_activity;
```

Useful for debugging connection issues.

---

### Exit PostgreSQL

```sql
\q
```

---

## Access PostgreSQL Without Entering Container

You can connect from your host machine if port 5432 is exposed:

```bash
psql -h localhost -U airflow -d analytics
```

---

## Common Troubleshooting

### Database does not exist

```text
FATAL: database "airflow" does not exist
```

Check available databases:

```sql
\l
```

Then connect to an existing database:

```bash
docker exec -it foundation_postgres psql -U airflow -d analytics
```

---

### Verify PostgreSQL is running

```bash
docker ps
```

Look for:

```text
foundation_postgres
```

---

### View PostgreSQL logs

```bash
docker logs foundation_postgres
```

---

### Check PostgreSQL readiness

```bash
docker exec foundation_postgres pg_isready -U airflow -d analytics
```

Expected:

```text
accepting connections
```