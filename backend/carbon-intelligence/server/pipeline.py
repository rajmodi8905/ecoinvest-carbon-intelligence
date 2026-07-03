import pathway as pw
import datetime

KAFKA_SERVERS = "kafka:9092"
KAFKA_SETTINGS = {
    "bootstrap.servers": KAFKA_SERVERS,
    "group.id": "carbon_pathway_consumer_v3",
    "auto.offset.reset": "earliest",
}

class DebeziumMessageSchema(pw.Schema):
    payload: pw.Json

def build_pipeline():
    print("🚀 Building Pathway pipeline...")

    # 1. Read from Kafka Streams
    verra_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS, topic="carbon.public.verra",
        format="json", schema=DebeziumMessageSchema, autocommit_duration_ms=1000
    )
    finance_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS, topic="carbon.public.finance",
        format="json", schema=DebeziumMessageSchema, autocommit_duration_ms=1000
    )
    news_raw = pw.io.kafka.read(
        rdkafka_settings=KAFKA_SETTINGS, topic="carbon.public.news",
        format="json", schema=DebeziumMessageSchema, autocommit_duration_ms=1000
    )

    # 2. Extract Data
    verra = verra_raw.filter(pw.this.payload["after"].is_not_none()).select(
        project_id=pw.this.payload["after"]["project_id"].as_str(),
        project_name=pw.this.payload["after"]["project_name"].as_str(),
        country=pw.this.payload["after"]["country"].as_str(),
        vintage=pw.this.payload["after"]["vintage"].as_int(),
        price=pw.this.payload["after"]["price"].as_float(),
        available_credits=pw.this.payload["after"]["available_credits"].as_int(),
        category=pw.this.payload["after"]["category"].as_str(),
    )

    finance = finance_raw.filter(pw.this.payload["after"].is_not_none()).select(
        ticker=pw.this.payload["after"]["ticker"].as_str(),
        company_name=pw.this.payload["after"]["company_name"].as_str(),
        industry=pw.this.payload["after"]["industry"].as_str(),
        stock_price=pw.this.payload["after"]["stock_price"].as_float(),
        change_percent=pw.this.payload["after"]["change_percent"].as_float(),
        esg_rating=pw.this.payload["after"]["esg_rating"].as_str(),
        timestamp=pw.this.payload["after"]["timestamp"].as_int(),
    )

    news = news_raw.filter(pw.this.payload["after"].is_not_none()).select(
        news_id=pw.this.payload["after"]["news_id"].as_str(),
        title=pw.this.payload["after"]["title"].as_str(),
        summary=pw.this.payload["after"]["summary"].as_str(),
        published=pw.this.payload["after"]["published"].as_str(),
        sentiment=pw.this.payload["after"]["sentiment"].as_str(),
        link=pw.this.payload["after"]["link"].as_str(),
        source=pw.this.payload["after"]["source"].as_str(),
    )

    # 3. Write basic output connectors
    pw.io.jsonlines.write(verra, "./output/projects.jsonl")
    pw.io.jsonlines.write(finance, "./output/finance.jsonl")
    pw.io.jsonlines.write(news, "./output/news.jsonl")

    # ==============================================================================
    # 4. ADVANCED STREAM ANALYTICS
    # ==============================================================================

    # A. Live ESG Sentiment Momentum Index
    # Continuously aggregates sentiment counts across the entire news stream
    sentiment_index = news.groupby(news.sentiment).reduce(
        sentiment=pw.this.sentiment,
        count=pw.reducers.count()
    )
    
    # B. Correlated Market Shocks (Cross-Stream Analysis)
    # Filter for companies whose stock drops > 1% (handling None values)
    dropping_stocks = finance.filter(pw.this.change_percent.is_not_none()).filter(pw.this.change_percent < -1.0)
    
    
    market_alerts = dropping_stocks.select(
        alert_type=pw.cast(str, "PRICE_DROP"),
        ticker=pw.this.ticker,
        company=pw.this.company_name,
        change=pw.this.change_percent,
        message=pw.coalesce(pw.this.company_name, "Unknown") + " is experiencing a significant drop (" + pw.cast(str, pw.this.change_percent) + "%). Monitoring live news feed.",
    )

    pw.io.jsonlines.write(sentiment_index, "./output/sentiment_index.jsonl")
    pw.io.jsonlines.write(market_alerts, "./output/market_alerts.jsonl")

    print("✅ Pathway pipeline ready with advanced analytics.")
    return verra, finance, news, sentiment_index, market_alerts
