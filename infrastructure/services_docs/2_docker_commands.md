# Docker Debugging & Inspection Commands

## Inspect Container Configuration

```bash
docker inspect foundation_postgres
```

Displays:

- environment variables
- mounts
- networking
- healthchecks
- image configuration
- container metadata

Think of this as the complete JSON definition of the running container.

---

## Show Healthcheck Configuration

```bash
docker inspect foundation_postgres | grep -A 20 Healthcheck
```

### What it does

| Part             | Meaning                            |
|------------------|------------------------------------|
| docker inspect   | Dump container metadata            |
| grep Healthcheck | Search for the Healthcheck section |
| -A 20            | Show 20 lines after the match      |

Example output:

```json
"Healthcheck": {
    "Test": [
        "CMD-SHELL",
        "pg_isready -U airflow"
    ]
}
```

Useful when debugging why a container is marked unhealthy.

---

## View Running Containers

```bash
docker ps
```

Shows:

- container names
- status
- ports
- uptime

---

## View All Containers

```bash
docker ps -a
```

Includes stopped containers.

---

## View Container Logs

```bash
docker logs foundation_postgres
```

Shows application output.

---

### Follow Logs Live

```bash
docker logs -f foundation_postgres
```

Equivalent to:

```bash
tail -f logfile.log
```

---

## Open Shell Inside Container

```bash
docker exec -it foundation_postgres sh
```

Opens a shell inside the running container.

Useful for:

- inspecting files
- checking permissions
- running commands manually

---

## Show Environment Variables

```bash
docker exec foundation_postgres env
```

Displays all environment variables loaded into the container.

---

## Check Mounted Volumes

```bash
docker inspect foundation_postgres | grep -A 20 Mounts
```

Shows:

- host paths
- Docker volumes
- container mount points

Useful for debugging missing files.

---

## Show Container IP Address

```bash
docker inspect foundation_postgres | grep IPAddress
```

Useful for networking troubleshooting.

---

## Show Container Resource Usage

```bash
docker stats
```

Displays:

- CPU usage
- memory usage
- network traffic
- disk I/O

Live updating dashboard.

---

## Check Container Health Status

```bash
docker inspect foundation_postgres --format='{{.State.Health.Status}}'
```

Possible results:

```text
healthy
unhealthy
starting
```

---

## Restart Container

```bash
docker restart foundation_postgres
```

Stops and starts the container.

---

## Stop Container

```bash
docker stop foundation_postgres
```

Gracefully shuts down the container.

---

## Remove Container

```bash
docker rm foundation_postgres
```

Deletes the container.

Does NOT delete Docker volumes.

---

## Show Docker Compose Services

```bash
docker compose ps
```

Displays:

- service names
- container names
- health status
- ports

---

## Rebuild Containers

```bash
docker compose up --build
```

Rebuilds Docker images before starting services.

Useful after changing Dockerfiles.

---

## Destroy Entire Stack

```bash
docker compose down
```

Removes:

- containers
- networks

Preserves volumes.

---

## Destroy Stack and Delete Data

```bash
docker compose down -v
```

Removes:

- containers
- networks
- volumes

WARNING:

This permanently deletes PostgreSQL data.

---

## Show Docker Volumes

```bash
docker volume ls
```

Example:

```text
infrastructure_postgres_data
infrastructure_timescale_data
```

---

## Inspect a Volume

```bash
docker volume inspect infrastructure_postgres_data
```

Shows where Docker stores the data on disk.

---

## Most Common Debugging Workflow

```bash
# Check services
docker compose ps

# View logs
docker logs -f foundation_postgres

# Check health
docker inspect foundation_postgres --format='{{.State.Health.Status}}'

# Enter container
docker exec -it foundation_postgres sh

# Connect to database
docker exec -it foundation_postgres psql -U airflow -d analytics
```

These five commands solve the majority of Docker and PostgreSQL debugging issues.