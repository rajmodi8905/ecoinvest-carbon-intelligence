# EcoInvest - Carbon Intelligence & ESG Investment Platform

A full-stack ESG and carbon market intelligence platform with real-time data scraping, AI-powered insights, RAG-based search, and interactive dashboards.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/jilsnshah/final_team58)

## 📚 Documentation

- [Deployment Guide](./DEPLOYMENT.md) - Complete deployment instructions for Vercel & cloud platforms
- [API Documentation](#) - Backend API reference
- [Architecture Overview](#architecture) - System design and data flow

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.13+ (for backend development)
- 8GB+ RAM recommended

### One-Command Startup

```bash
# Start entire infrastructure (frontend, backend, databases, etc.)
docker-compose up -d --build
```

That's it! Everything starts together:

- ✅ PostgreSQL Database (port 5432)
- ✅ Kafka & Zookeeper (messaging)
- ✅ Debezium (change data capture)
- ✅ Redis (caching)
- ✅ Pathway RAG Service (AI vectors)
- ✅ Data Scrapers (news, finance, projects)
- ✅ Flask Backend API (port 5001)

Frontend will be available at: http://localhost:5173

## 📊 What's Running

### Backend Services

| Service          | Port  | Description                |
| ---------------- | ----- | -------------------------- |
| **Backend API**  | 5001  | Flask REST API + WebSocket |
| **PostgreSQL**   | 5432  | Main database              |
| **Pathway gRPC** | 50051 | RAG/Vector search service  |
| **Kafka**        | 29092 | Message streaming          |
| **Debezium**     | 8083  | CDC connector              |
| **Redis**        | 6379  | Cache layer                |

### Data Sources

- **News**: 22 RSS feeds + NewsAPI (1000+ articles)
- **Finance**: Yahoo Finance (39 ESG stocks)
- **Projects**: Verra Registry (4,810+ carbon projects)
- **Updates**: Every 2 minutes

## 🎯 Features

### Dashboard

- Real-time news feed with sentiment analysis
- Company watchlist with ESG ratings
- Market analytics and trends
- Live data updates via WebSocket
- **AI Chatbot** - Comprehensive assistant with multi-tool access

### AI Chatbot (`/api/chat`)

Powered by **Ollama (qwen2.5)** with LangChain v1 agents:

**Capabilities:**
- 🔍 **RAG Search** - News & carbon projects vector search
- 📊 **Company Analysis** - Multi-level insights (basic → insights → future impact)
- 🌐 **Web Search** - Real-time internet search via Tavily
- 📈 **Project Reports** - AI-generated carbon project analysis
- 🧭 **Navigation** - Control frontend (theme, pages, watchlist)
- 💬 **Conversation Memory** - Persistent chat history per session
- ⚡ **Middleware** - Auto-trimming to 10 most recent messages

**Tools Available:**
- `search_carbon_news` - RAG search news articles
- `search_carbon_projects` - RAG search carbon projects
- `get_detailed_company_info` - Company details (stock, ESG, GII)
- `get_company_insights` - AI sustainability insights
- `get_company_future_impact` - Multi-agent future analysis
- `get_project_details` - Carbon project information
- `get_project_report` - AI project reports
- `list_available_companies` - Browse database
- `add_to_watchlist` / `remove_from_watchlist` - Manage watchlist
- `go_to_company` / `go_to_projects` - Navigate pages
- `change_theme` - Toggle dark/light mode

### Company Reports (`/api/company/:ticker`)

- **Basic Details** - Stock price, ESG rating, GII score
- **AI Insights** - Sustainability analysis powered by local LLM (Qwen) with PostgreSQL caching for instant reloads.
- **Future Impact Analysis** - Multi-agent system using:
  - News RAG search
  - Projects RAG search  
  - Internet search (Tavily)
  - Company data lookup
- **Custom Chat** - Ask anything about the company with conversation memory

### Projects Marketplace

- 4,810+ verified carbon projects
- Filter by country, category, price
- AI-generated project reports
- Real-time credit availability

## 🛠️ Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# - GOOGLE_API_KEY (required for AI features)
# - TAVILY_API_KEY (required for web search)
# - NEWS_API_KEY (optional, for NewsAPI scraping)

# Run locally (without Docker)
python app.py
```

### Frontend Development

```bash
# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Build for production
npm run build
```

### Environment Variables

Create a `.env` file in the project root:

```env
# Frontend Config
VITE_API_URL=http://localhost:5001
VITE_WS_URL=http://localhost:5001

# AI/LLM (Optional) - Docker Compose uses local Ollama by default
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional
NEWS_API_KEY=your_newsapi_key_here
```

(Note: If you run the backend locally without Docker, you should also have these in `backend/.env`)

**Get API Keys:**
- Google Gemini: https://makersuite.google.com/app/apikey
- Tavily Search: https://tavily.com/
- NewsAPI: https://newsapi.org/

## 📦 Tech Stack

### Frontend

- **React 18** + **Vite**
- **TailwindCSS** for styling
- **React Router** for navigation
- **Socket.IO** for real-time updates
- **Lucide Icons**

### Backend

- **Flask** + **Flask-SocketIO**
- **PostgreSQL** with CDC via Debezium
- **Pathway** for RAG/Vector search
- **Redis** for caching
- **Kafka** for event streaming

### AI/LLM Stack

- **Ollama (qwen2.5)** - Primary LLM (Local)
- **Google Gemini 2.0 Flash** - Alternative LLM via GOOGLE_API_KEY
- **LangChain v1** - Agent framework
- **LangGraph** - Agent orchestration with memory
- **Tavily** - Web search tool
- **FAISS** - Vector store for RAG
- **HuggingFace Embeddings** - sentence-transformers/all-MiniLM-L6-v2
- **RecursiveCharacterTextSplitter** - Text chunking (1000 chars, 200 overlap)

### Data Collection

- **22 RSS feeds** (Google News)
- **NewsAPI** integration
- **Yahoo Finance** API
- **Verra Registry** scraper
- **NewsAPI** integration
- **Yahoo Finance** API
- **Verra Registry** scraper

## 🔧 Useful Commands

### Docker Management

```bash
# Start everything
docker-compose up -d --build

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f scrapers

# Stop everything
docker-compose down

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d --build
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it carbon_postgres psql -U carbon -d carbon_intel

# Check data counts
docker exec carbon_postgres psql -U carbon -d carbon_intel -c "
  SELECT
    (SELECT COUNT(*) FROM news) as news_count,
    (SELECT COUNT(*) FROM finance) as finance_count,
    (SELECT COUNT(*) FROM verra) as projects_count;
"
```

### API Testing

```bash
# Test backend health
curl http://localhost:5001/api/analytics | jq

# Get companies
curl http://localhost:5001/api/companies | jq

# Get news
curl http://localhost:5001/api/news?limit=10 | jq

# Get projects
curl http://localhost:5001/api/projects?limit=10 | jq

# Get company insights
curl http://localhost:5001/api/company/TSLA/insights | jq
```

## 🐛 Troubleshooting

### Backend not accessible

- Check if Docker containers are running: `docker ps`
- Verify backend logs: `docker-compose logs backend`
- Ensure port 5001 is not in use: `lsof -i :5001`

### No data showing

- Wait 2-3 minutes for scrapers to populate data
- Check scraper logs: `docker-compose logs scrapers`
- Verify database: `docker exec carbon_postgres psql -U carbon -d carbon_intel -c "SELECT COUNT(*) FROM news;"`

### Frontend errors

- Clear browser cache
- Reinstall dependencies: `rm -rf node_modules package-lock.json && npm install`
- Check API URL in `.env` file

### Scrapers not updating

- Check NEWS_API_KEY is configured in `backend/.env`
- View scraper logs: `docker-compose logs -f scrapers`
- Restart scrapers: `docker-compose restart scrapers`

## 📈 Performance

- **Backend**: Handles 1000+ requests/min
- **Database**: 5000+ projects, 1000+ news articles
- **Scraper**: Updates every 2 minutes
- **WebSocket**: Real-time updates every 10 seconds
- **Cache**: Redis for sub-second response times
- **RAG Search**: FAISS vector search with incremental updates
- **AI Agents**: Multi-tool orchestration with LangGraph memory

## 🌐 Production Deployment

**Frontend**: Deployed on Vercel (automatic deployments from `main` branch)
**Backend**: Deploy on Railway, Render, or Heroku (see [DEPLOYMENT.md](./DEPLOYMENT.md))

### Quick Deploy to Vercel

1. Fork/clone this repository
2. Push to your GitHub
3. Import to Vercel
4. Add environment variables:
   - `VITE_API_URL` - Your backend URL
   - `VITE_WS_URL` - Your backend WebSocket URL
5. Deploy!

See [complete deployment guide](./DEPLOYMENT.md) for backend options.

## 🔐 Security Notes

- Change default PostgreSQL password in production
- Never commit API keys to git
- Use environment variables for secrets (see `.env.example`)
- Enable CORS only for trusted domains
- API keys required: `GOOGLE_API_KEY`, `TAVILY_API_KEY`

## 🤖 AI Architecture

### RAG Services (Incremental Updates)

**News RAG** (`services/news_rag_service.py`):
- Monitors `news.jsonl` for changes
- Uses MD5 hashing (title|link|published) to track indexed articles
- Only adds new articles to FAISS vector store
- Background thread checks every 60 seconds
- Returns: title, source, link, published, sentiment, content, score

**Projects RAG** (`services/projects_rag_service.py`):
- Monitors `projects.jsonl` for changes
- Uses MD5 hashing (project_id|name|registry) to track indexed projects
- Incremental FAISS updates only
- Returns: name, registry, country, type, methodology, status, content, score

### Agent Middleware

**Message Limiting** (`@before_agent` decorator):
- Automatically trims conversations to 10 most recent messages
- Prevents token overflow
- Applied to both aibot and company chat agents

### LangChain v1 Migration

Updated from v0 to v1 with:
- `create_agent()` from `langchain.agents`
- `@before_agent` middleware from `langchain.agents.middleware`
- `MemorySaver` from `langgraph.checkpoint.memory`
- `system_prompt` parameter instead of `prompt`
- Thread-based memory via `config={"configurable": {"thread_id": "..."}}`

---
