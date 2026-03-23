# EcoInvest — Architecture Deep Dive

This document describes the five-layer architecture of the EcoInvest platform,
from raw data ingestion through to the React frontend.

<!-- Screenshot: Full system architecture diagram or deployment topology -->

---

## Layer 1 — Data Ingestion (Scrapers)

Three Python scrapers run on a 2-minute polling cycle inside Docker:

| Scraper | Source | Table |
|---|---|---|
| `verra_scraper.py` | Verra Registry HTTP API | `public.verra` |
| `finance_scraper_yfinance.py` | Yahoo Finance (`yfinance`) | `public.finance` |
| `news_scraper.py` | 22 RSS feeds + NewsAPI | `public.news` |
| `carbonmark_scraper.py` | Carbonmark marketplace API | `public.carbonmark` |

Scrapers perform upserts (`INSERT … ON CONFLICT DO UPDATE`) so that every
write — whether a new record or a price/sentiment update — generates a WAL event
that Debezium can capture.

---

## Layer 2 — Change Data Capture (PostgreSQL WAL + Debezium)

PostgreSQL is configured with `wal_level = logical` in `db/postgres.conf`.
This enables logical decoding, which allows external tools to subscribe to a
replication slot and receive a structured stream of row-level changes.

Debezium Connect (port 8083) hosts a single PostgreSQL connector defined in
`debezium/connector.json`.  The connector:

1. Connects to the `carbon_slot` logical replication slot on the `carbon_intel`
   database.
2. Monitors four tables: `public.verra`, `public.carbonmark`, `public.finance`,
   `public.news`.
3. Publishes each row change as a JSON message to a Kafka topic whose name is
   `{topic.prefix}.{schema}.{table}`.

Resulting Kafka topics:

| Topic | Source table |
|---|---|
| `carbon.public.verra` | Verra Registry projects |
| `carbon.public.carbonmark` | Carbonmark marketplace listings |
| `carbon.public.finance` | Yahoo Finance ESG stocks |
| `carbon.public.news` | News articles |

Each Kafka message has the structure:

```json
{
  "schema": { ... },
  "payload": {
    "before": { ... },
    "after":  { ... },
    "op": "c"
  }
}
```

`op` values: `"c"` = INSERT, `"u"` = UPDATE, `"d"` = DELETE, `"r"` = snapshot
read (initial table snapshot on first connector start).

---

## Layer 3 — Streaming Pipeline (Pathway)

Pathway (`carbon_pathway` Docker service, port 50051 gRPC) consumes the four
Kafka topics and processes them in two complementary functions:

### `build_pipeline()` — JSON envelope path

Uses `pw.io.kafka.read()` with `format="json"` and a minimal
`DebeziumMessageSchema` to read raw Debezium envelopes.

**DELETE filtering:**
```python
verra = verra_raw.filter(pw.this.payload["after"].is_not_none())
```
When `op == "d"`, Debezium sets `payload.after` to `null`.  The filter
predicate `.is_not_none()` silently drops these events so deleted rows do not
appear in the output JSONL files.

**Type coercion:**
JSON scalars arrive as untyped nodes.  `.as_str()`, `.as_int()`, and
`.as_float()` cast them to Python-native types so downstream consumers
receive predictable data without additional parsing.

Outputs are written to:
- `output/projects.jsonl` — Verra project records
- `output/finance.jsonl` — ESG stock records
- `output/news.jsonl` — News articles

### `run_pathway()` — Native Debezium path

Uses `pw.io.debezium.read()` which natively parses the Debezium envelope and
exposes `.after` directly as a typed attribute according to the provided schema.
This path produces a unified `projects + finance` join and a separate
`finance.jsonl`, served by the gRPC server.

### Incremental computation

Pathway uses a differential dataflow model: when a row changes, only the delta
propagates through the operator graph.  Each output record carries a `diff`
field (weight):
- `diff = 1` → new or updated row (add to downstream state)
- `diff = -1` → retracted row (remove from downstream state)

This is fundamentally different from Spark/Flink micro-batch models, where the
entire window is recomputed regardless of how many rows changed.

---

## Layer 4 — Caching (Redis)

The Flask API reads the JSONL output files through `pathway_reader.py` and
caches the parsed results in Redis (port 6379) with a configurable TTL.  Cache
hits serve responses in ~120 ms; cache misses trigger a JSONL re-read (~450 ms).

The RAG services (news and projects) also use the JSONL files as their document
corpus.  A background thread checks for file changes every 60 seconds and calls
`faiss.add()` only for documents whose MD5 hash has not been seen before.

---

## Layer 5 — API & Frontend

**Flask API** (`backend/app.py`, port 5001):
- REST endpoints: `/api/analytics`, `/api/companies`, `/api/news`,
  `/api/projects`, `/api/company/:ticker/insights`
- WebSocket (Flask-SocketIO): pushes live data updates every 10 seconds
- AI endpoints: `/api/chat` (LangGraph chatbot), `/api/report` (project reports),
  `/api/company/:ticker/report` (RAG company bot)

**React Frontend** (port 5173):
- Dashboard: real-time news feed, company watchlist, market analytics
- Projects Marketplace: filter 4,810+ projects by country, category, price
- Report Page: AI-generated project reports

---

## Full Pipeline Diagram

```
Verra Registry  ─────────────────────────────────────────────────────────────┐
Yahoo Finance   ──► Scrapers (Python, every 2 min) ──► PostgreSQL 15        │
NewsAPI / RSS   ─────────────────────────────────────  (WAL logical)         │
Carbonmark API  ──────────────────────────────────────────────────────────────┘
                                                               │
                                                    Debezium Connect (port 8083)
                                                    logical replication slot
                                                    carbon_slot on carbon_intel
                                                               │
                                          ┌────────────────────────────────────┐
                                          │         Apache Kafka (port 9092)   │
                                          │  carbon.public.verra               │
                                          │  carbon.public.carbonmark          │
                                          │  carbon.public.finance             │
                                          │  carbon.public.news                │
                                          └────────────────────────────────────┘
                                                               │
                                                  Pathway (pw.io.kafka.read /
                                                   pw.io.debezium.read)
                                                  filter DELETEs
                                                  type-coerce fields
                                                  incremental diff computation
                                                               │
                                          ┌────────────────────────────────────┐
                                          │         JSONL output files         │
                                          │  output/projects.jsonl             │
                                          │  output/finance.jsonl              │
                                          │  output/news.jsonl                 │
                                          └────────────────────────────────────┘
                                                               │
                                                    Redis Cache (port 6379)
                                                    TTL-based response cache
                                                    FAISS incremental indexing
                                                               │
                                                  Flask REST API (port 5001)
                                                  + Flask-SocketIO WebSocket
                                                               │
                                                  React Frontend (port 5173)
                                                  Vite + TailwindCSS + Recharts
```
