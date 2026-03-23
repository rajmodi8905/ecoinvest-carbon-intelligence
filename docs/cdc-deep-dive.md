# CDC Deep Dive — Change Data Capture in EcoInvest

This document explains how Change Data Capture (CDC) works in EcoInvest, from
the PostgreSQL Write-Ahead Log through Debezium and Kafka into the Pathway
streaming pipeline.

---

## What Is Change Data Capture?

Change Data Capture is a pattern for reliably detecting and propagating
row-level changes (inserts, updates, deletes) from a source database to
downstream consumers without polling the database repeatedly.  Instead of
running `SELECT * FROM table WHERE updated_at > last_run`, CDC reads the
database's internal change log — in PostgreSQL's case the Write-Ahead Log
(WAL) — and converts every committed change into a structured event.

In EcoInvest, CDC solves a fundamental problem: the scrapers write new carbon
project data, stock prices, and news articles every two minutes, but the
Pathway streaming pipeline and the React frontend should reflect those changes
in under two seconds.  Without CDC this would require either very frequent
polling (expensive, inconsistent) or a custom event bus wired into every
scraper (fragile, tightly coupled).

---

## How PostgreSQL WAL Works

PostgreSQL writes every committed transaction to the Write-Ahead Log before
applying it to the heap files.  The WAL is primarily a crash-recovery
mechanism, but PostgreSQL also supports **logical decoding** of the WAL —
transforming the low-level binary WAL records into higher-level row change
events that external tools can consume.

### Enabling logical replication

In `db/postgres.conf`:

```
wal_level = logical
```

`wal_level = logical` is required (not `replica` or `minimal`) because it adds
the extra information needed for logical decoding: the old row values for
UPDATE and DELETE events, and the ability to filter changes by table.

A **replication slot** (`carbon_slot`) is created by Debezium on first connect.
The slot acts as a named cursor in the WAL: PostgreSQL guarantees it will not
remove WAL segments until the slot consumer has read past them, ensuring no
events are lost even if Debezium restarts.

---

## How Debezium Reads the WAL

Debezium Connect (port 8083) runs the
`io.debezium.connector.postgresql.PostgresConnector` defined in
`debezium/connector.json`.  The connector:

1. Opens a logical replication connection to PostgreSQL using the
   `pgoutput` output plugin (built into PostgreSQL 10+).
2. Reads decoded WAL events from the `carbon_slot` replication slot.
3. Transforms each event into a structured JSON envelope.
4. Publishes the envelope to a Kafka topic named
   `{topic.prefix}.{schema_name}.{table_name}`.

The `topic.prefix` is `"carbon"`, so changes to `public.verra` appear on
`carbon.public.verra`, etc.

---

## Debezium Event Structure

Every Kafka message published by Debezium has the following shape:

```json
{
  "schema": { "...": "Kafka Connect schema descriptor" },
  "payload": {
    "before": {
      "project_id": "VCS-1234",
      "project_name": "Amazon REDD+ Forest Protection",
      "...": "previous column values (null for INSERT)"
    },
    "after": {
      "project_id": "VCS-1234",
      "project_name": "Amazon REDD+ Forest Protection — Updated",
      "...": "new column values (null for DELETE)"
    },
    "source": {
      "db": "carbon_intel",
      "table": "verra",
      "lsn": 12345678,
      "ts_ms": 1711180800000
    },
    "op": "u",
    "ts_ms": 1711180800123
  }
}
```

**`op` field values:**

| Value | Meaning |
|---|---|
| `"c"` | CREATE (INSERT) |
| `"u"` | UPDATE |
| `"d"` | DELETE |
| `"r"` | READ (initial snapshot, sent once on first connector start) |

For INSERT: `before` is `null`, `after` contains the new row.
For UPDATE: both `before` and `after` contain the old and new values.
For DELETE: `before` contains the deleted row, `after` is `null`.

---

## How Pathway Consumes from Kafka

The pipeline uses two Pathway Kafka connectors depending on the code path:

### `pw.io.kafka.read()` — raw JSON envelope

```python
verra_raw = pw.io.kafka.read(
    rdkafka_settings=KAFKA_SETTINGS,
    topic="carbon.public.verra",
    format="json",
    schema=DebeziumMessageSchema,
    autocommit_duration_ms=1000,
)
```

This reads the full Debezium JSON envelope into a single `payload: pw.Json`
column.  Field extraction and DELETE filtering happen explicitly in the next
step.

### `pw.io.debezium.read()` — native Debezium connector

```python
verra_stream = pw.io.debezium.read(
    rdkafka_settings,
    topic_name="carbon.public.verra",
    schema=VerraSchema,
    autocommit_duration_ms=1000,
)
```

Pathway's native Debezium connector parses the envelope automatically and
exposes `.before` and `.after` as typed attributes matching the provided schema.
This is cleaner when the schema is known ahead of time.

---

## Filtering DELETE Events

For the `pw.io.kafka.read()` path, DELETE events are identified by
`payload.after == null` and removed before field extraction:

```python
verra = verra_raw.filter(pw.this.payload["after"].is_not_none()).select(
    project_id=pw.this.payload["after"]["project_id"].as_str(),
    ...
)
```

This ensures:
1. The downstream JSONL files never contain rows with `null` field values.
2. The FAISS vector store is not indexed with empty documents.
3. The Flask API does not serve stale or deleted records.

For the `pw.io.debezium.read()` path, Pathway handles DELETE propagation
natively through its differential dataflow model — a DELETE event causes
Pathway to emit a retraction record (`diff = -1`) for the affected row, which
downstream operators interpret as a removal.

---

## Pathway's Incremental Computation Model

Unlike Spark Streaming (micro-batch: recompute the entire window every N
seconds) or Flink (dataflow with explicit state backends and checkpointing),
Pathway uses a **differential dataflow** model:

- Each row in a Pathway table carries a **diff weight** (+1 or -1).
- When a row changes, Pathway emits two records: a retraction (`diff = -1`)
  for the old value and an addition (`diff = +1`) for the new value.
- Operators (filter, select, join) propagate only the changed rows — not
  the full dataset — so the computational cost is proportional to the size
  of the change, not the size of the table.

This means that when a single stock price is updated, only one record flows
through the entire pipeline to update `finance.jsonl` — not all 39 stocks.

The `diff` field is visible in the output JSONL files and is read by
`pathway_reader.py` to apply incremental updates to the in-memory cache.

---

## CDC Flow Diagram

```
PostgreSQL WAL (wal_level = logical)
  carbon_intel database
  carbon_slot replication slot
          │
          ▼
Debezium Connect (port 8083)
  PostgresConnector
  plugin: pgoutput
  tables: public.verra, public.carbonmark, public.finance, public.news
          │
          ▼ JSON envelope { before, after, op, source }
Kafka Topics (port 9092)
  carbon.public.verra
  carbon.public.carbonmark
  carbon.public.finance
  carbon.public.news
          │
          ▼
Pathway pw.io.kafka.read / pw.io.debezium.read
  filter: payload["after"].is_not_none()  ← drops DELETE events
  select: type-coerce fields (.as_str / .as_int / .as_float)
  incremental differential dataflow
          │
          ▼
JSONL output (diff = +1 / -1)
  output/projects.jsonl
  output/finance.jsonl
  output/news.jsonl
          │
          ▼
Redis Cache
  pathway_reader.py applies diff records to in-memory state
  FAISS services index new documents (MD5-gated)
          │
          ▼
Flask REST API (port 5001)
  < 2 seconds data freshness end-to-end
```
