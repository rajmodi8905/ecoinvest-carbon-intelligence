# EcoInvest — Carbon Credit Market Intelligence Platform

Real-time carbon credit market intelligence with streaming CDC pipelines, multi-agent AI analysis, and RAG-powered search. Built for Inter-IIT Tech Meet 14.0.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Pathway](https://img.shields.io/badge/Pathway-streaming-FF6B35)](https://pathway.com)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-7.5-231F20?logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-Pro-4285F4?logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![LangChain](https://img.shields.io/badge/LangChain-v1-1C3C3C)](https://langchain.com)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![CI](https://github.com/rajmodi8905/ecoinvest-carbon-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/rajmodi8905/ecoinvest-carbon-intelligence/actions/workflows/ci.yml)

---

## What This Does & Why It's Hard

EcoInvest ingests carbon credit data from Verra, Yahoo Finance, and NewsAPI into PostgreSQL, then propagates every row-level change — inserts, updates, and deletes — through Debezium CDC and Kafka into a Pathway streaming pipeline that maintains incrementally updated JSONL outputs with sub-2-second data freshness. On top of this live data layer, three specialized AI agents handle project report generation, conversational dashboard intelligence (with LangGraph memory), and retrieval-augmented company analysis using incremental FAISS vector indexing. The hardest part is keeping the entire chain — from database write to UI render — consistent, low-latency, and cost-efficient without a dedicated data engineering team.

<!-- Screenshot: Dashboard overview showing real-time news feed, company watchlist, and market analytics widgets -->

---

## Features

- **Real-time streaming pipeline**: PostgreSQL WAL → Debezium CDC → Kafka → Pathway; data freshness under 2 seconds end-to-end
- **4,810+ verified carbon projects** from the Verra Registry with live credit availability and pricing
- **39 ESG stocks** tracked via Yahoo Finance with market cap, ESG rating, GII score, and change percent
- **1,000+ news articles** from 22 RSS feeds and NewsAPI, each tagged with sentiment analysis
- **Dashboard AI Chatbot**: Gemini 2.0 Flash + LangGraph with 15 tool calls (RAG search, company analysis, web search, navigation, watchlist management)
- **Project Report Agent**: Gemini Pro generates structured markdown reports for any carbon project on demand
- **Company RAG Bot**: FAISS-indexed, HuggingFace-embedded retrieval with MD5-based incremental indexing to avoid redundant re-ingestion
- **Redis caching** cuts repeat API query latency from ~450 ms to ~120 ms
- **WebSocket push** delivers live data updates to the React frontend every 10 seconds

---

## Architecture

```
Data Sources
  Verra Registry  ──┐
  Yahoo Finance   ──┤──► Scrapers (Python) ──► PostgreSQL 15
  NewsAPI / RSS   ──┘       (every 2 min)      (WAL: wal_level=logical)
                                                       │
                                              Debezium Connect (port 8083)
                                              reads pg_logical replication slot
                                                       │
                                               Kafka Topics (port 9092)
                                               carbon.public.verra
                                               carbon.public.finance
                                               carbon.public.news
                                               carbon.public.carbonmark
                                                       │
                                           Pathway Pipeline (pw.io.kafka.read)
                                           filter DELETE events (after == null)
                                           type-coerce fields (.as_str/.as_int)
                                           write incremental JSONL outputs
                                                       │
                                              Redis Cache (port 6379)
                                              (projects.jsonl / news.jsonl / finance.jsonl)
                                                       │
                                             Flask REST API (port 5001)
                                             + Flask-SocketIO WebSocket
                                                       │
                                              React Frontend (port 5173)
                                              Vite + TailwindCSS + Recharts
```

<!-- Screenshot: Architecture diagram rendered in the platform or a whiteboard export -->

---

## AI Agents

### 1. Project Report Agent (Gemini Pro)
Generates structured, markdown-formatted investment reports for any carbon project on demand. It pulls project metadata from the database, enriches it with live news via RAG search, and synthesises a report covering methodology, registry status, credit availability, and risk assessment.

### 2. Dashboard Chatbot (Gemini 2.0 Flash + LangGraph)
A multi-tool conversational agent with 15 registered tools including RAG news and project search, company insights (basic → insights → future impact), web search via Tavily, frontend navigation, watchlist management, and theme control. LangGraph's `MemorySaver` maintains per-session conversation history keyed by `thread_id`; a `@before_agent` middleware trims messages to the 10 most recent to prevent token overflow.

### 3. Company Report RAG Bot (Gemini + FAISS)
Uses `RecursiveCharacterTextSplitter` (1,000-char chunks, 200-char overlap) with HuggingFace `all-MiniLM-L6-v2` embeddings stored in a FAISS vector store. An MD5 hash (title|link|published) is computed for each document before indexing; only documents whose hash has not been seen are added, making index updates fully incremental. Retrieval results are cited inline in the response to ground the answer and reduce hallucination rate.

<!-- Screenshot: Company report page showing RAG-powered Q&A alongside stock chart and ESG metrics -->

---

## Key Technical Decisions

### Why Pathway over Apache Flink
The Pathway CDC pipeline is implemented in **205 lines** versus the equivalent Flink job (~800+ lines). Pathway's declarative, Python-native API eliminates boilerplate state management and natively consumes Debezium-format Kafka events via `pw.io.debezium.read()`, while Flink requires a separate Debezium deserialiser, custom state stores, and a Java/Scala operator graph. Pathway's incremental computation model (differential dataflow) also means only changed rows propagate downstream — not entire micro-batches.

### Hybrid Inference Strategy
Tool-call steps that require low-latency decisions (intent classification, tool selection) use Groq-hosted models for sub-100 ms inference. Deep reasoning steps — sustainability analysis, multi-paragraph report generation, synthesis across multiple retrieved chunks — use Gemini Pro/Flash, which provides higher context windows and better long-form coherence at ~$0.001 per query.

### Incremental FAISS Indexing with MD5 Hashing
Instead of rebuilding the vector store on every scrape cycle, each article and project document is hashed (MD5 of key fields). A persisted set of seen hashes means the background indexing thread only calls `faiss.add()` for genuinely new documents. This reduces compute overhead by ~40% on typical scrape cycles where 90%+ of documents are unchanged.

---

## Results & Metrics

| Metric | Before | After |
|---|---|---|
| Data Freshness | 15–60 min (batch) | < 2 seconds (streaming) |
| Query Latency (cached) | ~450 ms | ~120 ms |
| RAG Context Retrieval Hit Rate | — | 92% |
| Hallucination Rate | — | < 3% |
| Avg RAG Response Time | — | 1.2 s |
| Compute Overhead Reduction | — | ~40% |
| Cost per Query | — | ~$0.001 |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (frontend development)
- Python 3.10+ (backend development)
- 8 GB+ RAM recommended

### One-Command Startup

```bash
# Clone the repository
git clone https://github.com/rajmodi8905/ecoinvest-carbon-intelligence.git
cd ecoinvest-carbon-intelligence

# Start entire backend infrastructure
docker-compose up -d --build

# Start frontend (in a new terminal)
npm install
npm run dev
```

Services started:

| Service | Port | Description |
|---|---|---|
| **Backend API** | 5001 | Flask REST API + WebSocket |
| **PostgreSQL** | 5432 | Primary database (WAL enabled) |
| **Pathway gRPC** | 50051 | Streaming pipeline + RAG output |
| **Kafka** | 29092 | Event streaming (external) |
| **Debezium** | 8083 | CDC connector REST API |
| **Redis** | 6379 | Response cache |

Frontend: http://localhost:5173

### Environment Variables

Copy and fill in the required keys:

```bash
cp backend/.env.example backend/.env
```

```env
# Required for all AI features
GOOGLE_API_KEY=your_gemini_api_key_here

# Required for web search tool
TAVILY_API_KEY=your_tavily_api_key_here

# Optional — enables NewsAPI scraping in addition to RSS
NEWS_API_KEY=your_newsapi_key_here
```

Get API keys:
- Google Gemini: https://makersuite.google.com/app/apikey
- Tavily: https://tavily.com/
- NewsAPI: https://newsapi.org/

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite, TailwindCSS, React Router, Recharts, Socket.IO Client |
| **Backend** | Flask 3, Flask-SocketIO, Python 3.10+ |
| **AI / LLM** | Google Gemini Pro & 2.0 Flash, LangChain v1, LangGraph, FAISS, HuggingFace Embeddings, Tavily |
| **Data Pipeline** | Pathway (streaming), Apache Kafka, Debezium CDC |
| **Database / Cache** | PostgreSQL 15 (WAL logical replication), Redis 7 |
| **Infrastructure** | Docker Compose, Vercel (frontend) |

---

## Project Structure

```
ecoinvest-carbon-intelligence/
├── src/                          # React frontend
│   ├── components/               # Navbar, DashboardChatSidebar
│   ├── pages/                    # Dashboard, ProjectsPage, ReportPage
│   ├── services/api.js           # Axios API client
│   └── context/ThemeContext.jsx  # Dark/light mode
├── backend/
│   ├── app.py                    # Flask application entry point
│   ├── aibot.py                  # Dashboard chatbot (LangGraph agent)
│   ├── llm_manager.py            # LLM client initialisation
│   ├── pathway_reader.py         # Reads Pathway JSONL output files
│   ├── frontend_actions.py       # WebSocket frontend action emitter
│   ├── requirements.txt          # Python dependencies
│   └── services/
│       ├── news_rag_service.py   # Incremental FAISS RAG for news
│       ├── projects_rag_service.py # Incremental FAISS RAG for projects
│       ├── project_report_service.py # Gemini Pro report generator
│       ├── company_service.py    # Stock + ESG data lookups
│       ├── analytics_service.py  # Market analytics aggregation
│       └── live_news_service.py  # Live feed with sentiment
├── backend/carbon-intelligence/
│   ├── server/
│   │   ├── pipeline.py           # Pathway streaming pipeline
│   │   ├── grpc_server.py        # gRPC server for pipeline data
│   │   ├── schemas.py            # Pathway table schemas
│   │   └── redis_cache.py        # Redis caching helpers
│   ├── scrapers/
│   │   ├── verra_scraper.py      # Verra Registry scraper
│   │   ├── finance_scraper_yfinance.py # Yahoo Finance scraper
│   │   └── news_scraper.py       # RSS + NewsAPI scraper
│   ├── debezium/
│   │   ├── connector.json        # Debezium connector configuration
│   │   └── README.md             # Debezium setup and debug guide
│   └── db/
│       ├── init.sql              # Schema + WAL configuration
│       └── postgres.conf         # PostgreSQL config (wal_level=logical)
├── docs/
│   ├── architecture.md           # 5-layer architecture deep dive
│   ├── cdc-deep-dive.md          # CDC, WAL, Debezium, Pathway explainer
│   └── ai-agents.md              # Multi-agent system documentation
├── docker-compose.yml            # Root-level frontend + backend compose
├── RESULTS.md                    # Benchmarking and evaluation results
├── CONTRIBUTING.md               # Development guide
└── .github/workflows/ci.yml      # GitHub Actions CI
```

<!-- Screenshot: Repository structure or IDE view of the project -->

---

## 📚 Documentation

- [Architecture Deep Dive](./docs/architecture.md)
- [CDC & Streaming Explainer](./docs/cdc-deep-dive.md)
- [AI Agents Documentation](./docs/ai-agents.md)
- [Debezium Setup Guide](./backend/carbon-intelligence/debezium/README.md)
- [Performance Results](./RESULTS.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Contributing](./CONTRIBUTING.md)

---

## Useful Commands

```bash
# View logs for a service
docker-compose logs -f backend
docker-compose logs -f scrapers

# Reset database (deletes all data)
docker-compose down -v && docker-compose up -d --build

# Connect to PostgreSQL
docker exec -it carbon_postgres psql -U carbon -d carbon_intel

# Test API endpoints
curl http://localhost:5001/api/analytics | jq
curl http://localhost:5001/api/companies | jq
curl http://localhost:5001/api/projects?limit=10 | jq
curl http://localhost:5001/api/company/TSLA/insights | jq
```

---

## Security Notes

- Change the default PostgreSQL password (`carbonpw`) before any public deployment
- Never commit `.env` files — use `.env.example` as a template
- Restrict CORS origins to trusted domains in production (`flask-cors` config in `app.py`)
- Required secrets: `GOOGLE_API_KEY`, `TAVILY_API_KEY`
