# CarbonMark Terminal: Real-Time ESG Intelligence & Carbon Credit Bloomberg Terminal

CarbonMark Terminal is a high-performance, real-time ESG and Carbon Market Intelligence dashboard modeled after the Bloomberg Terminal. It combines low-latency streaming data pipelines, hybrid RAG semantic search, and multi-agent AI systems to provide deep-dive analysis on carbon-exposed equities and carbon offset projects.

## 🚀 Key Architectural Pillars

```
                     ┌───────────────────┐
                     │   Data Scrapers   │ (Yahoo Finance, News RSS, Verra Registry)
                     └─────────┬─────────┘
                               │ (Writes)
                               ▼
                     ┌───────────────────┐
                     │    PostgreSQL     │ (Main Database)
                     └─────────┬─────────┘
                               │ (Change Data Capture)
                               ▼
                     ┌───────────────────┐
                     │ Debezium Connect  │
                     └─────────┬─────────┘
                               │ (Streams CDC Events)
                               ▼
                     ┌───────────────────┐
                     │   Apache Kafka    │ (Distributed Event Streaming)
                     └─────────┬─────────┘
                               │ (Low-latency Stream Enrichment)
                               ▼
                     ┌───────────────────┐
                     │ Pathway Engine &  │ ◄─── (Vector Search &
                     │   gRPC Service    │       Live Signal Calculations)
                     └─────────┬─────────┘
                               │ (WebSocket / REST API)
                               ▼
                     ┌───────────────────┐
                     │  React Frontend   │ (Bloomberg UI & Live Signals)
                     └───────────────────┘
```

1. **Low-Latency Streaming Pipeline (Kafka & Debezium CDC)**
   - Captures transactions and raw data updates in PostgreSQL via **Debezium CDC** (Change Data Capture).
   - Publishes database events into **Apache Kafka** topics to ensure distributed, backpressure-resistant event streaming.
   - **Pathway Streaming Engine** consumes these Kafka topics directly, processing streaming data windows to calculate live risk indexes, sentiment metrics, and momentum indicators on-the-fly.

2. **Advanced Hybrid RAG Semantic Search**
   - Implements a hybrid search combining **FAISS dense vector embeddings** (vectorizing descriptions using `nomic-embed-text`) and **BM25 sparse keyword search**.
   - Leverages **Reciprocal Rank Fusion (RRF)** to merge dense and sparse results with customized weighting (favoring keyword intent for precise queries).
   - Integrates **Dynamic Score Thresholding** to prune low-relevance results, preventing false-positive noise in the UI.

3. **Multi-Agent Decision Systems**
   - Powered by **Google Gemini** (or fallback local **Ollama** models) using LangChain agents.
   - Implements custom tools for financial extraction, SWOT analysis, and project sustainability reporting.
   - Utilizes asynchronous streaming architectures to stream reasoning traces token-by-token directly to the user interface.

4. **Robust Cache Layer**
   - High-throughput **Redis Caching** for company detail lookups and API responses.
   - Fallback persistent caching directly inside PostgreSQL to ensure sub-millisecond page reload times for highly analytical reports.

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, Vanilla CSS (Bloomberg Terminal inspired theme), WebSockets.
- **Backend**: Flask API, Gunicorn, PostgreSQL, Redis.
- **Data Engineering**: Apache Kafka, Confluent Schema Registry, Debezium CDC, Pathway (streaming framework).
- **AI/RAG**: LangChain, FAISS Vector Index, BM25, Gemini API / Ollama (`nomic-embed-text`, `qwen2.5`).

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM allocated to Docker

### Environment Setup
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_api_key
NEWS_API_KEY=your_news_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### Starting the Platform
Launch the entire containerized architecture with a single command:
```bash
docker compose up -d --build
```

Once all containers are running and healthy:
- **Frontend Dashboard**: http://localhost:5173
- **Backend API**: http://localhost:5001
- **Pathway gRPC**: Port `50051`
- **Debezium Connect REST API**: Port `8083`

---

## 📈 Platform Features & Navigation

- **📺 Terminal Dashboard**: View active watchlist, live scrolling ticker tape of carbon-exposed assets, and global market statistics updating in real-time.
- **⚡ Live Enriched Signals**: Columns labeled `RISK`, `MOMENTUM`, and `SENT 24H` are calculated in real-time by Pathway as news feeds ingest. Pathway-computed assets are badged with a `⚡` icon.
- **🔍 RAG Carbon Project Search**: Search over 4,800+ Verra registry projects using natural language (e.g., *"mangrove projects in india"*). The search uses hybrid RAG to show the most relevant projects first.
- **🤖 Real-time AI Agent**: Click the floating chatbot in the bottom right corner. It can navigate the UI, toggle themes, generate deep SWOT reports on carbon offsets, and explain live market events.
