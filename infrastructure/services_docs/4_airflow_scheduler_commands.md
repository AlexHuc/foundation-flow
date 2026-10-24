# Apache Airflow Operations Guide (Docker + Airflow 2.7.x)

## Overview

This document contains the most useful Apache Airflow commands for:

* Webserver administration
* Scheduler administration
* DAG management
* Task management
* User management
* Database management
* Troubleshooting
* Docker operations

Assumptions:

* Docker Compose deployment
* Scheduler container: foundation_airflow_scheduler
* Webserver container: foundation_airflow_webserver
* Airflow version: 2.7.3

---

# 1. Container Management

## Start Airflow
```bashbash
docker compose up -d airflow-scheduler airflow-webserver
```

## Stop Airflow
```bash
docker compose stop airflow-scheduler airflow-webserver
```

## Restart Airflow
```bash
docker compose restart airflow-scheduler airflow-webserver
```

## Rebuild Containers
```bash
docker compose build --no-cache
docker compose up -d
```

## View Running Containers
```bash
docker compose ps
```

## View Container Status
```bash
docker ps
```

---

# 2. Enter Containers

## Enter Scheduler Container
```bash
docker exec -it foundation_airflow_scheduler bash
```

## Enter Webserver Container
```bash
docker exec -it foundation_airflow_webserver bash
```

---

# 3. Airflow Version

## Check Installed Version
```bash
docker exec -it foundation_airflow_scheduler airflow version
```

---

# 4. DAG Management

## List All DAGs
```bash
docker exec -it foundation_airflow_scheduler airflow dags list
```

## List DAG Import Errors
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-import-errors
```

## Show DAG Details
```bash
docker exec -it foundation_airflow_scheduler airflow dags show <dag_id>
```

Example:
```bash
docker exec -it foundation_airflow_scheduler airflow dags show yahoo_fetch_daily_prices
```

## Trigger DAG Manually
```bash
docker exec -it foundation_airflow_scheduler airflow dags trigger <dag_id>
```

Example:
```bash
docker exec -it foundation_airflow_scheduler airflow dags trigger yahoo_fetch_daily_prices
```

## Pause DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags pause <dag_id>
```

## Unpause DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags unpause <dag_id>
```

## Delete DAG Runs
```bash
docker exec -it foundation_airflow_scheduler airflow dags delete <dag_id>
```

## List DAG Runs
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-runs -d <dag_id>
```

## Backfill DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags backfill 
--start-date 2024-01-01 
--end-date 2024-01-31 
<dag_id>
```

---

# 5. Task Management

## List Tasks
```bash
docker exec -it foundation_airflow_scheduler airflow tasks list <dag_id>
```

## Test Task
```bash
docker exec -it foundation_airflow_scheduler airflow tasks test 
<dag_id> 
<task_id> 
2024-01-01
```

## Clear Task State
```bash
docker exec -it foundation_airflow_scheduler airflow tasks clear <dag_id>
```

## List Task States
```bash
docker exec -it foundation_airflow_scheduler airflow tasks states-for-dag-run 
<dag_id> 
<run_id>
```

---

# 6. User Management

## List Users
```bash
docker exec -it foundation_airflow_scheduler airflow users list
```

## Create User
```bash
docker exec -it foundation_airflow_scheduler airflow users create 
--username admin 
--firstname Admin 
--lastname User 
--role Admin 
--email [admin@example.com](mailto:admin@example.com) 
--password admin
```

## Delete User
```bash
docker exec -it foundation_airflow_scheduler airflow users delete 
--username admin
```

## Reset Password
```bash
docker exec -it foundation_airflow_scheduler airflow users reset-password 
--username admin 
--password new_password
```

---

# 7. Connections Management

## List Connections
```bash
docker exec -it foundation_airflow_scheduler airflow connections list
```

## Get Connection
```bash
docker exec -it foundation_airflow_scheduler airflow connections get postgres_default
```

## Add Connection
```bash
docker exec -it foundation_airflow_scheduler airflow connections add 
my_postgres 
--conn-type postgres 
--conn-host localhost 
--conn-login user 
--conn-password password 
--conn-schema database 
--conn-port 5432
```

## Delete Connection
```bash
docker exec -it foundation_airflow_scheduler airflow connections delete my_postgres
```

---

# 8. Variables Management

## List Variables
```bash
docker exec -it foundation_airflow_scheduler airflow variables list
```

## Get Variable
```bash
docker exec -it foundation_airflow_scheduler airflow variables get my_variable
```

## Set Variable
```bash
docker exec -it foundation_airflow_scheduler airflow variables set my_variable value
```

## Delete Variable
```bash
docker exec -it foundation_airflow_scheduler airflow variables delete my_variable
```

---

# 9. Scheduler Operations

## Check Scheduler Logs
```bash
docker logs foundation_airflow_scheduler
```

## Follow Scheduler Logs
```bash
docker logs -f foundation_airflow_scheduler
```

## Restart Scheduler
```bash
docker compose restart airflow-scheduler
```

## Check Scheduler Health
```bash
docker exec -it foundation_airflow_scheduler airflow jobs check 
--job-type SchedulerJob
```

---

# 10. Webserver Operations

## Check Webserver Logs
```bash
docker logs foundation_airflow_webserver
```

## Follow Webserver Logs
```bash
docker logs -f foundation_airflow_webserver
```

## Restart Webserver
```bash
docker compose restart airflow-webserver
```

## Check Health Endpoint
```bash
curl http://localhost:8080/health
```

---

# 11. Database Operations

## Check Current Database Connection
```bash
docker exec -it foundation_airflow_scheduler airflow config get-value database sql_alchemy_conn
```

## Database Health Check
```bash
docker exec -it foundation_airflow_scheduler airflow db check
```

## Upgrade Database
```bash
docker exec -it foundation_airflow_scheduler airflow db upgrade
```

## Initialize Database
```bash
docker exec -it foundation_airflow_scheduler airflow db init
```

## Reset Database (DANGER)
```bash
docker exec -it foundation_airflow_scheduler airflow db reset
```

WARNING: Deletes all Airflow metadata.

---

# 12. DAG Discovery Troubleshooting

## Verify DAG Files
```bash
docker exec -it foundation_airflow_scheduler ls -R /opt/airflow/dags
```

## Verify Scheduler Sees DAGs
```bash
docker exec -it foundation_airflow_scheduler airflow dags list
```

## Verify Import Errors
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-import-errors
```

## Search Scheduler Logs
```bash
docker logs foundation_airflow_scheduler | grep ERROR
```

---

# 13. Airflow Configuration

## Show Entire Configuration
```bash
docker exec -it foundation_airflow_scheduler airflow config list
```

## Show Single Configuration Value
```bash
docker exec -it foundation_airflow_scheduler airflow config get-value core dags_folder
```

Examples:
```bash
airflow config get-value core executor

airflow config get-value core dags_folder

airflow config get-value database sql_alchemy_conn
```
---

# 14. Useful Docker Debug Commands

## Container Health
```bash
docker inspect foundation_airflow_scheduler
```

## Resource Usage
```bash
docker stats
```

## View Environment Variables
```bash
docker exec -it foundation_airflow_scheduler env
```

## Check Mounted Volumes
```bash
docker inspect foundation_airflow_scheduler | grep -A 20 Mounts
```

---

# 15. Most Common Daily Commands

## Start Airflow
```bash
docker compose up -d airflow-scheduler airflow-webserver
```

## Check DAGs
```bash
docker exec -it foundation_airflow_scheduler airflow dags list
```

## Check Import Errors
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-import-errors
```

## Trigger DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags trigger yahoo_fetch_daily_prices
```

## Watch Scheduler Logs
```bash
docker logs -f foundation_airflow_scheduler
```

## Watch Webserver Logs
```bash
docker logs -f foundation_airflow_webserver
```

## List Users
```bash
docker exec -it foundation_airflow_scheduler airflow users list
```

## Access UI
```bash
http://localhost:8080
```

Default Example Credentials:
```bash
Username: admin
Password: admin
```

---

# 16. Useful Commands for Your Current Setup

## Unpause Your DAGs
```bash
docker exec -it foundation_airflow_scheduler airflow dags unpause yahoo_fetch_daily_prices

docker exec -it foundation_airflow_scheduler airflow dags unpause yahoo_fetch_fundamentals
```

## Trigger Daily Prices DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags trigger yahoo_fetch_daily_prices
```

## Trigger Fundamentals DAG
```bash
docker exec -it foundation_airflow_scheduler airflow dags trigger yahoo_fetch_fundamentals
```

## List Runs for Daily Prices
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-runs 
-d yahoo_fetch_daily_prices
```

## List Runs for Fundamentals
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-runs 
-d yahoo_fetch_fundamentals
```

## Check Scheduler Can See DAGs
```bash
docker exec -it foundation_airflow_scheduler airflow dags list | grep yahoo
```

## Verify No Import Errors
```bash
docker exec -it foundation_airflow_scheduler airflow dags list-import-errors
```
