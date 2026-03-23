import pathway as pw
from schemas import CarbonmarkSchema, FinanceSchema, NewsSchema, VerraSchema

# Kafka broker address — matches the Docker Compose service name
KAFKA_SERVERS = "kafka:9092"

# Common rdkafka settings shared across all consumer calls.
# "earliest" applies only when the consumer group has no committed offset yet
# (e.g. on first run or after a consumer group reset).  On subsequent runs
# Pathway resumes from the last committed offset, so historical events are not
# replayed a second time.
KAFKA_SETTINGS = {
    "bootstrap.servers": KAFKA_SERVERS,
    "group.id": "carbon_pathway_consumer_v2",
    "auto.offset.reset": "earliest",
}


# Minimal schema for raw Debezium JSON envelopes.
# Debezium wraps every row change in:
#   { "schema": {...}, "payload": { "before": {...}, "after": {...}, "op": "c|u|d" } }
# We only need the "payload" key here; field extraction happens after filtering.
class DebeziumMessageSchema(pw.Schema):
    payload: pw.Json


def build_pipeline():
    """
    Production pipeline: reads raw Debezium JSON envelopes from four Kafka
    topics, filters out DELETE events, extracts typed fields, and writes
    incremental JSONL output files consumed by the Flask API.
    """
    print("🚀 Building Pathway pipeline...")

    # --- Kafka source connectors ------------------------------------------
    # pw.io.kafka.read() creates a live, append-only Pathway table that grows
    # as new Kafka messages arrive.  format="json" deserialises each message
    # body into the supplied schema.  autocommit_duration_ms controls how
    # frequently the consumer commits its offset back to Kafka (1 s here).

    # Verra Registry carbon project records (inserts + updates + deletes)
    verra_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.verra",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=1000,
    )

    # Carbonmark marketplace listings
    carbon_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.carbonmark",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=1000,
    )

    # Yahoo Finance ESG stock records
    finance_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.finance",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=1000,
    )

    # News articles from RSS feeds and NewsAPI
    news_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS,
        topic="carbon.public.news",
        format="json",
        schema=DebeziumMessageSchema,
        autocommit_duration_ms=1000,
    )

    # --- DELETE event filtering -------------------------------------------
    # In a Debezium CDC event the "after" field contains the new row state for
    # INSERT and UPDATE operations.  For DELETE operations Debezium sets
    # "after" to null (the row no longer exists).  We filter those out so that
    # deleted rows are simply excluded from the output rather than propagated
    # downstream as empty records.
    #
    # .filter(pw.this.payload["after"].is_not_none()) keeps only INSERT/UPDATE
    # events and silently drops DELETE events.

    # --- Field extraction & type coercion ---------------------------------
    # .select() projects the raw JSON envelope into a flat, typed row.
    # .as_str() / .as_int() / .as_float() coerce the JSON scalar values
    # (which arrive as untyped JSON nodes) into Python-native types so that
    # downstream consumers receive predictable, strongly-typed data.

    verra = verra_raw.filter(pw.this.payload["after"].is_not_none()).select(
        project_id=pw.this.payload["after"]["project_id"].as_str(),
        project_name=pw.this.payload["after"]["project_name"].as_str(),
        description=pw.this.payload["after"]["description"].as_str(),
        methodology=pw.this.payload["after"]["methodology"].as_str(),
        registry_status=pw.this.payload["after"]["registry_status"].as_str(),
        country=pw.this.payload["after"]["country"].as_str(),
        # vintage is a four-digit year stored as an integer in PostgreSQL
        vintage=pw.this.payload["after"]["vintage"].as_int(),
        price=pw.this.payload["after"]["price"].as_float(),
        # available_credits tracks remaining tradeable volume
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
        # amount is a float representing tonnes of CO₂ equivalent
        amount=pw.this.payload["after"]["amount"].as_float(),
        project_summary=pw.this.payload["after"]["project_summary"].as_str(),
        project_link=pw.this.payload["after"]["project_link"].as_str(),
    )

    finance = finance_raw.filter(pw.this.payload["after"].is_not_none()).select(
        ticker=pw.this.payload["after"]["ticker"].as_str(),
        company_name=pw.this.payload["after"]["company_name"].as_str(),
        industry=pw.this.payload["after"]["industry"].as_str(),
        description=pw.this.payload["after"]["description"].as_str(),
        # gii_score = Green Innovation Index, integer 0-100
        gii_score=pw.this.payload["after"]["gii_score"].as_int(),
        stock_price=pw.this.payload["after"]["stock_price"].as_float(),
        market_cap=pw.this.payload["after"]["market_cap"].as_str(),
        sustainability_update=pw.this.payload["after"]["sustainability_update"].as_str(),
        esg_rating=pw.this.payload["after"]["esg_rating"].as_str(),
        website=pw.this.payload["after"]["website"].as_str(),
        price=pw.this.payload["after"]["price"].as_float(),
        # volume is total shares traded in the last session (integer)
        volume=pw.this.payload["after"]["volume"].as_int(),
        change_percent=pw.this.payload["after"]["change_percent"].as_float(),
        # timestamp is a Unix epoch integer from Yahoo Finance
        timestamp=pw.this.payload["after"]["timestamp"].as_int(),
    )

    news = news_raw.filter(pw.this.payload["after"].is_not_none()).select(
        news_id=pw.this.payload["after"]["news_id"].as_str(),
        title=pw.this.payload["after"]["title"].as_str(),
        summary=pw.this.payload["after"]["summary"].as_str(),
        link=pw.this.payload["after"]["link"].as_str(),
        published=pw.this.payload["after"]["published"].as_str(),
        source=pw.this.payload["after"]["source"].as_str(),
        # sentiment is "positive" / "negative" / "neutral" assigned by scraper
        sentiment=pw.this.payload["after"]["sentiment"].as_str(),
    )

    # --- JSONL output sinks -----------------------------------------------
    # pw.io.jsonlines.write() emits one JSON object per row per diff event.
    # In Pathway's incremental computation model, a "diff" record carries a
    # weight of +1 (new/updated row) or -1 (retracted row).  The downstream
    # pathway_reader.py and RAG services read these files and interpret the
    # weight field (diff=1 means live row, diff=-1 means retracted/deleted).
    pw.io.jsonlines.write(verra, "./output/projects.jsonl")
    pw.io.jsonlines.write(finance, "./output/finance.jsonl")
    pw.io.jsonlines.write(news, "./output/news.jsonl")

    print("✅ Pathway pipeline ready with output connectors.")
    return verra, finance, news



def run_pathway():
    """
    Alternative pipeline using pw.io.debezium.read() which handles the
    Debezium envelope unpacking natively, exposing .before and .after
    attributes directly on the stream row.  Used for the gRPC server path.
    """
    print("🚀 Running Pathway pipeline...")

    rdkafka_settings = {
        "bootstrap.servers": KAFKA_SERVERS,
        "group.id": "carbon_pathway_consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": "true",
        "auto.commit.interval.ms": "1000",
    }

    # pw.io.debezium.read() is a first-class Pathway connector for Debezium
    # streams.  It parses the Debezium envelope automatically and makes the
    # "before" and "after" sub-objects accessible as typed attributes using
    # the provided schema.  This is simpler than manually parsing the JSON
    # payload, but requires the schema to exactly match the PostgreSQL table.

    # Verra Registry stream — one event per INSERT/UPDATE/DELETE on public.verra
    verra_stream = pw.io.debezium.read(
        rdkafka_settings,
        topic_name="carbon.public.verra",
        schema=VerraSchema,
        autocommit_duration_ms=1000,
    )
    
    # Project the "after" state into a flat table; "before" is ignored because
    # we only need the current row value, not the previous value.
    verra_table = verra_stream.select(
        project_id=verra_stream.after.project_id,
        project_name=verra_stream.after.project_name,
        registry_status=verra_stream.after.registry_status,
        country=verra_stream.after.country,
        vintage=verra_stream.after.vintage,
        supply=verra_stream.after.supply,
        project_summary=verra_stream.after.project_summary,
        project_link=verra_stream.after.project_link,
    )
    
    # Carbonmark marketplace stream — tracks available listings and amounts
    carbonmark_stream = pw.io.debezium.read(
        rdkafka_settings,
        topic_name="carbon.public.carbonmark",
        schema=CarbonmarkSchema,
        autocommit_duration_ms=1000,
    )
    
    carbonmark_table = carbonmark_stream.select(
        project_id=carbonmark_stream.after.project_id,
        project_name=carbonmark_stream.after.project_name,
        vintage=carbonmark_stream.after.vintage,
        amount=carbonmark_stream.after.amount,
        project_summary=carbonmark_stream.after.project_summary,
        project_link=carbonmark_stream.after.project_link,
    )
    
    # Finance stream — ESG stock data from Yahoo Finance scraper
    finance_stream = pw.io.debezium.read(
        rdkafka_settings,
        topic_name="carbon.public.finance",
        schema=FinanceSchema,
        autocommit_duration_ms=1000,
    )
    
    finance_table = finance_stream.select(
        ticker=finance_stream.after.ticker,
        price=finance_stream.after.price,
        volume=finance_stream.after.volume,
        market_cap=finance_stream.after.market_cap,
        change_percent=finance_stream.after.change_percent,
        # timestamp is a Unix epoch integer used for ordering and freshness checks
        timestamp=finance_stream.after.timestamp,
    )
    
    # Outer join: merge Carbonmark marketplace listings with Verra project
    # metadata on project_id.  An outer join is used so that projects without
    # a Carbonmark listing (or vice versa) are still represented in the output.
    unified_table = carbonmark_table.join(verra_table, carbonmark_table.project_id == verra_table.project_id, how="outer").select(
        project_id=carbonmark_table.project_id,
        project_name=carbonmark_table.project_name,
        registry_status=verra_table.registry_status,
        country=verra_table.country,
        vintage=verra_table.vintage,
        supply=verra_table.supply,
        amount=carbonmark_table.amount,
        price=finance_table.price,
        volume=finance_table.volume,
        market_cap=finance_table.market_cap,
        change_percent=finance_table.change_percent,
        timestamp=finance_table.timestamp,
    )

    # Write unified project+market data for the gRPC server to serve
    pw.io.jsonlines.write(unified_table, "/app/output/unified.jsonl")
    
    # Write finance-only data for market analytics endpoints
    pw.io.jsonlines.write(finance_table, "/app/output/finance.jsonl")

    print("✅ Pathway pipeline run complete.")
    return unified_table, finance_table
