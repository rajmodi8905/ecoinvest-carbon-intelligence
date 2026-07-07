import pathway as pw

KAFKA_SERVERS = "kafka:9092"

KAFKA_SETTINGS = {
    "bootstrap.servers": KAFKA_SERVERS,
    "group.id": "carbon_pathway_consumer_v2",
    "auto.offset.reset": "earliest",
    "fetch.wait.max.ms": "10",
    "linger.ms": "5",
}


class DebeziumMessageSchema(pw.Schema):
    payload: pw.Json


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
        news_id=pw.this.payload["after"]["news_id"].as_str(),
        title=pw.this.payload["after"]["title"].as_str(),
        summary=pw.this.payload["after"]["summary"].as_str(),
        link=pw.this.payload["after"]["link"].as_str(),
        published=pw.this.payload["after"]["published"].as_str(),
        source=pw.this.payload["after"]["source"].as_str(),
        sentiment=pw.this.payload["after"]["sentiment"].as_str(),
    )

    # Write outputs directly without complex joins
    pw.io.jsonlines.write(verra, "./output/projects.jsonl")
    pw.io.jsonlines.write(finance, "./output/finance.jsonl")
    pw.io.jsonlines.write(news, "./output/news.jsonl")

    print("✅ Pathway pipeline ready with output connectors.")
    return verra, finance, news



def run_pathway():
    print("🚀 Running Pathway pipeline...")

    rdkafka_settings = {
        "bootstrap.servers": KAFKA_SERVERS,
        "group.id": "carbon_pathway_consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": "true",
        "auto.commit.interval.ms": "1000",
    }

    # Read Verra stream
    verra_stream = pw.io.debezium.read(
        rdkafka_settings,
        topic_name="carbon.public.verra",
        schema=VerraSchema,
        autocommit_duration_ms=1000,
    )
    
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
    
    # Read Carbonmark stream
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
    
    # Read Finance stream
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
        timestamp=finance_stream.after.timestamp,
    )
    
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

    # Write unified data
    pw.io.jsonlines.write(unified_table, "/app/output/unified.jsonl")
    
    # Write finance data
    pw.io.jsonlines.write(finance_table, "/app/output/finance.jsonl")

    print("✅ Pathway pipeline run complete.")
    return unified_table, finance_table
