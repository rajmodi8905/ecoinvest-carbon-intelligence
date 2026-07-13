"""
Pathway Streaming Pipeline — Carbon Intelligence

Data flow:
  Kafka (Debezium CDC) → Pathway → JSONL files + pathway_enriched (Postgres)

The pipeline:
1. Reads Debezium CDC events from 4 Kafka topics (verra, carbonmark, finance, news)
2. Writes clean JSONL snapshots for the gRPC server to serve
3. Computes live enriched signals (sentiment_24h, news_velocity, risk) per company
   and writes them to the `pathway_enriched` Postgres table every ~30 seconds.
   The Flask backend reads from this table to show the ⚡ live-computed badge.
"""

import pathway as pw
import psycopg2
import os
import re
import json
import time
import threading
import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

KAFKA_SERVERS = "kafka:9092"

KAFKA_SETTINGS = {
    "bootstrap.servers": KAFKA_SERVERS,
    "group.id": "carbon_pathway_consumer_v2",
    "auto.offset.reset": "earliest",
    "fetch.wait.max.ms": "10",
    "linger.ms": "5",
}

# DB config — use env vars (same as grpc_server.py)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "carbon_intel"),
    "user": os.getenv("DB_USER", "carbon"),
    "password": os.getenv("DB_PASSWORD", "carbonpw"),
}


class DebeziumMessageSchema(pw.Schema):
    payload: pw.Json


# ─────────────────────────────────────────────────────────────────────────────
# Pathway Enriched Writer
# Runs in a background thread; reads from Postgres directly (news + finance),
# computes per-company live signals, and upserts to pathway_enriched.
# This is the write path for the ⚡ live-signals badge in the frontend.
# ─────────────────────────────────────────────────────────────────────────────

def _compute_and_write_enriched():
    """
    Background thread that computes per-company enriched signals from live data
    and writes them to the pathway_enriched table every 30 seconds.

    Signals computed:
      - sentiment_24h : mean sentiment score over last 24h news mentions
      - news_velocity : count of news mentions in last 24h
      - risk          : composite risk score [0, 1]
    """
    print("⚡ pathway_enriched writer starting...")
    ESG_MAP = {"AAA": 100, "AA": 90, "A": 80, "BBB": 70, "BB": 60, "B": 50, "CCC": 40}
    SENTIMENT_MAP = {"Positive": 1.0, "Negative": -1.0, "Neutral": 0.0}

    def _get_conn():
        return psycopg2.connect(**DB_CONFIG)

    # Give the rest of the system time to initialize before first run
    time.sleep(15)

    consecutive_errors = 0

    while True:
        try:
            conn = _get_conn()
            cur = conn.cursor()

            # 1. Load all companies
            cur.execute("""
                SELECT ticker, company_name, industry, esg_rating, gii_score, price, change_percent
                FROM finance
            """)
            companies = cur.fetchall()

            if not companies:
                cur.close()
                conn.close()
                time.sleep(30)
                continue

            # 2. Load recent news (last 48h window for velocity, 24h for signals)
            cur.execute("""
                SELECT title, summary, sentiment, source
                FROM news
                WHERE published > NOW() - INTERVAL '48 hours'
            """)
            news_rows = cur.fetchall()

            # 3. Build per-company news signals via regex matching
            now_ts = datetime.now(timezone.utc).timestamp()
            signals = {}

            for (ticker, company_name, industry, esg_rating, gii_score, price, change_pct) in companies:
                parts = [re.escape(ticker)] if ticker else []
                if company_name and len(company_name) > 3:
                    parts.append(re.escape(company_name))
                if not parts:
                    continue

                pat = re.compile(
                    r'\b(' + '|'.join(parts) + r')\b', re.IGNORECASE
                )

                matched_sentiments = []
                news_count = 0

                for (title, summary, sentiment, source) in news_rows:
                    text = (title or "") + " " + (summary or "")
                    if pat.search(text):
                        matched_sentiments.append(
                            SENTIMENT_MAP.get(sentiment or "Neutral", 0.0)
                        )
                        news_count += 1

                mean_sentiment = (
                    sum(matched_sentiments) / len(matched_sentiments)
                    if matched_sentiments else 0.0
                )

                # Risk: composite from sentiment + price change
                s_norm = (mean_sentiment + 1) / 2  # [-1,1] → [0,1]
                chg = float(change_pct or 0)
                p_neg = max(0.0, -chg / 100.0)
                risk = round(((1 - s_norm) * (1 + 0.5 * p_neg)) / 2.0, 4)

                signals[ticker] = {
                    "sentiment_24h": round(mean_sentiment, 4),
                    "news_velocity": news_count,
                    "risk": risk,
                }

            # 4. Upsert into pathway_enriched
            upserted = 0
            for ticker, sigs in signals.items():
                for metric_key, metric_value in sigs.items():
                    cur.execute("""
                        INSERT INTO pathway_enriched
                            (entity_type, entity_id, metric_key, metric_value, computed_at)
                        VALUES ('company', %s, %s, %s, NOW())
                        ON CONFLICT (entity_type, entity_id, metric_key) DO UPDATE SET
                            metric_value = EXCLUDED.metric_value,
                            computed_at  = NOW()
                    """, (ticker, metric_key, float(metric_value)))
                    upserted += 1

            conn.commit()
            cur.close()
            conn.close()

            print(f"⚡ pathway_enriched: upserted {upserted} signals for "
                  f"{len(signals)} companies")
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            print(f"⚠️ pathway_enriched writer error (#{consecutive_errors}): {e}")
            if consecutive_errors >= 5:
                print("❌ pathway_enriched writer: too many consecutive errors, "
                      "sleeping 120s before retry")
                time.sleep(120)
                consecutive_errors = 0

        # Run every 30 seconds
        time.sleep(30)


def start_enriched_writer():
    """Start the pathway_enriched background writer thread."""
    t = threading.Thread(
        target=_compute_and_write_enriched,
        daemon=True,
        name="pathway-enriched-writer"
    )
    t.start()
    print("✅ pathway_enriched writer thread started")
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline():
    print("🚀 Building Pathway pipeline...")

    # Read from Debezium CDC streams using JSON format
    # Debezium wraps everything in {schema: ..., payload: {before:..., after:...}}

    verra_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.verra",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=100,
    )

    carbon_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.carbonmark",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=100,
    )

    finance_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.finance",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=100,
    )

    news_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.news",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=100,
    )

    # Filter out DELETE events (where payload.after is null) and extract fields
    verra = verra_raw.filter(pw.this.payload["after"].is_not_none()).select(
        project_id=pw.this.payload["after"]["project_id"].as_str(),
        project_name=pw.this.payload["after"]["project_name"].as_str(),
        description=pw.this.payload["after"]["description"].as_str(),
        methodology=pw.this.payload["after"]["methodology"].as_str(),
        registry_status=pw.this.payload["after"]["registry_status"].as_str(),
        country=pw.this.payload["after"]["country"].as_str(),
        vintage=pw.this.payload["after"]["vintage"].as_int(),
        price=pw.this.payload["after"]["price"].as_float(),
        available_credits=pw.this.payload["after"]["available_credits"].as_int(),
        category=pw.this.payload["after"]["category"].as_str(),
        image_url=pw.this.payload["after"]["image_url"].as_str(),
        buy_link=pw.this.payload["after"]["buy_link"].as_str(),
        project_summary=pw.this.payload["after"]["project_summary"].as_str(),
    )

    carbon = carbon_raw.filter(pw.this.payload["after"].is_not_none()).select(
        project_id=pw.this.payload["after"]["project_id"].as_str(),
        project_name=pw.this.payload["after"]["project_name"].as_str(),
        vintage=pw.this.payload["after"]["vintage"].as_int(),
        amount=pw.this.payload["after"]["amount"].as_float(),
        project_summary=pw.this.payload["after"]["project_summary"].as_str(),
        project_link=pw.this.payload["after"]["project_link"].as_str(),
    )

    finance = finance_raw.filter(pw.this.payload["after"].is_not_none()).select(
        ticker=pw.this.payload["after"]["ticker"].as_str(),
        company_name=pw.this.payload["after"]["company_name"].as_str(),
        industry=pw.this.payload["after"]["industry"].as_str(),
        description=pw.this.payload["after"]["description"].as_str(),
        gii_score=pw.this.payload["after"]["gii_score"].as_int(),
        stock_price=pw.this.payload["after"]["stock_price"].as_float(),
        market_cap=pw.this.payload["after"]["market_cap"].as_str(),
        sustainability_update=pw.this.payload["after"]["sustainability_update"].as_str(),
        esg_rating=pw.this.payload["after"]["esg_rating"].as_str(),
        website=pw.this.payload["after"]["website"].as_str(),
        price=pw.this.payload["after"]["price"].as_float(),
        volume=pw.this.payload["after"]["volume"].as_int(),
        change_percent=pw.this.payload["after"]["change_percent"].as_float(),
        timestamp=pw.this.payload["after"]["timestamp"].as_int(),
    )

    news = news_raw.filter(pw.this.payload["after"].is_not_none()).select(
        news_id=pw.this.payload["after"]["id"].as_str(),
        title=pw.this.payload["after"]["title"].as_str(),
        summary=pw.this.payload["after"]["summary"].as_str(),
        link=pw.this.payload["after"]["link"].as_str(),
        published=pw.this.payload["after"]["published"].as_str(),
        source=pw.this.payload["after"]["source"].as_str(),
        sentiment=pw.this.payload["after"]["sentiment"].as_str(),
    )

    # Write outputs directly — consumed by gRPC servicer via JSONL read
    pw.io.jsonlines.write(verra,   "./output/projects.jsonl")
    pw.io.jsonlines.write(finance, "./output/finance.jsonl")
    pw.io.jsonlines.write(news,    "./output/news.jsonl")

    # ── Start the pathway_enriched writer background thread ──────────────────
    # This computes per-company signals from Postgres and writes to
    # pathway_enriched every 30s. Flask backend reads this for the ⚡ badge.
    start_enriched_writer()

    print("✅ Pathway pipeline ready with output connectors.")
    print("⚡ pathway_enriched writer: running every 30s in background")
    # Return all three live tables for use in grpc_server.py
    return verra, finance, news
