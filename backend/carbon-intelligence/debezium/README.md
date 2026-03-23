# Debezium Setup & Debugging Guide

This guide covers the `connector.json` configuration, how to verify the
connector is running, how to observe Kafka topics receiving events, and how to
diagnose common failure modes.

---

## connector.json — Field Reference

```json
{
  "name": "postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "carbon",
    "database.password": "carbonpw",
    "database.dbname": "carbon_intel",
    "topic.prefix": "carbon",
    "slot.name": "carbon_slot",
    "plugin.name": "pgoutput",
    "publication.autocreate.mode": "all_tables",
    "schema.include.list": "public",
    "table.include.list": "public.verra,public.carbonmark,public.finance,public.news"
  }
}
```

| Field | Value | Meaning |
|---|---|---|
| `connector.class` | `io.debezium.connector.postgresql.PostgresConnector` | Use the Debezium PostgreSQL connector plugin |
| `database.hostname` | `postgres` | Docker Compose service name for the PostgreSQL container |
| `database.port` | `5432` | Standard PostgreSQL port |
| `database.user` | `carbon` | Database user with `REPLICATION` privilege |
| `database.password` | `carbonpw` | Password for the above user |
| `database.dbname` | `carbon_intel` | Target database name |
| `topic.prefix` | `carbon` | Prefix for all Kafka topic names: `carbon.{schema}.{table}` |
| `slot.name` | `carbon_slot` | Name of the PostgreSQL logical replication slot |
| `plugin.name` | `pgoutput` | Logical decoding plugin — `pgoutput` is built into PostgreSQL 10+ |
| `publication.autocreate.mode` | `all_tables` | Auto-create a publication covering all tables (or use `filtered` with `table.include.list`) |
| `schema.include.list` | `public` | Only capture changes in the `public` schema |
| `table.include.list` | `public.verra,...` | Capture changes only from these four tables |

---

## Verifying the Connector Is Running

### Check connector status

```bash
# List all registered connectors
curl http://localhost:8083/connectors

# Get the status of the postgres-connector
curl http://localhost:8083/connectors/postgres-connector/status | jq
```

A healthy response looks like:

```json
{
  "name": "postgres-connector",
  "connector": { "state": "RUNNING", "worker_id": "debezium:8083" },
  "tasks": [
    { "id": 0, "state": "RUNNING", "worker_id": "debezium:8083" }
  ],
  "type": "source"
}
```

If `state` is `FAILED`, check the Debezium logs:

```bash
docker-compose logs debezium_connect | tail -50
```

### Check connector config

```bash
curl http://localhost:8083/connectors/postgres-connector/config | jq
```

---

## Checking Kafka Topics Are Receiving Events

### List topics

```bash
docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --list | grep carbon
```

Expected output:
```
carbon.public.carbonmark
carbon.public.finance
carbon.public.news
carbon.public.verra
```

### Consume messages from a topic

```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic carbon.public.verra \
  --from-beginning \
  --max-messages 3 \
  | python3 -m json.tool
```

Each message should be a Debezium JSON envelope with `payload.before`,
`payload.after`, and `payload.op` fields.

### Check consumer group lag

```bash
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group carbon_pathway_consumer_v2
```

A `LAG` of 0 means the Pathway pipeline has consumed all available events.

---

## Registering the Connector Manually

If the `debezium_setup` container did not run successfully on first start, you
can register the connector manually:

```bash
curl -X POST http://localhost:8083/connectors \
  -H 'Content-Type: application/json' \
  -d @backend/carbon-intelligence/debezium/connector.json
```

To delete and recreate it (useful after a schema change):

```bash
curl -X DELETE http://localhost:8083/connectors/postgres-connector
curl -X POST http://localhost:8083/connectors \
  -H 'Content-Type: application/json' \
  -d @backend/carbon-intelligence/debezium/connector.json
```

---

## Common Failure Modes

### `FAILED` state: replication slot already exists

**Error in logs:**
```
ERROR: replication slot "carbon_slot" already exists
```

**Fix:** Drop the slot from PostgreSQL and restart the connector.

```bash
docker exec carbon_postgres psql -U carbon -d carbon_intel \
  -c "SELECT pg_drop_replication_slot('carbon_slot');"
curl -X DELETE http://localhost:8083/connectors/postgres-connector
curl -X POST http://localhost:8083/connectors \
  -H 'Content-Type: application/json' \
  -d @backend/carbon-intelligence/debezium/connector.json
```

### No events on Kafka topics

**Possible causes:**
1. `wal_level` is not `logical` in PostgreSQL — verify with:
   ```bash
   docker exec carbon_postgres psql -U carbon -d carbon_intel \
     -c "SHOW wal_level;"
   ```
   Expected: `logical`.  If not, the `postgres.conf` volume mount is not
   working — check the Docker Compose volume path.

2. The Debezium connector is in `RUNNING` state but no data has been inserted
   yet.  Wait for the scrapers to run their first cycle (up to 2 minutes), or
   trigger a manual insert:
   ```bash
   docker exec carbon_postgres psql -U carbon -d carbon_intel \
     -c "UPDATE verra SET updated_at = now() WHERE id = (SELECT id FROM verra LIMIT 1);"
   ```

### Pathway not consuming events

**Check Pathway logs:**
```bash
docker-compose logs carbon_pathway | tail -30
```

If Pathway started before Kafka was ready, it may have failed to connect.
Restart it:

```bash
docker-compose restart carbon_pathway
```

### Debezium Connect not reachable (port 8083 not responding)

**Check Debezium container status:**
```bash
docker ps | grep debezium
docker-compose logs debezium_connect | tail -20
```

Debezium takes up to 30 seconds to start.  The `healthcheck` in
`docker-compose.yml` polls `http://localhost:8083/` every 10 seconds; wait
for it to show `healthy` before attempting to register the connector.
