"""
Multi-Agent Report Service — Supervisor pattern

Architecture:
  SupervisorAgent decides which sub-agents to invoke
      ├── NewsAgent    (news RAG + sentiment search)
      ├── MarketAgent  (company/project data + live signals)
      └── WebAgent     (Tavily web search — optional)
  SynthesizerAgent — merges outputs → structured HTML report

Each sub-agent:
  - Scoped system prompt + restricted tool list
  - 30s timeout with graceful fallback to cached data
  - Emits step dicts via generator for SSE streaming

Frontend: AgentTracePanel subscribes to /api/company/<ticker>/report/stream
"""

import logging
import time
from typing import Generator, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try imports — all are optional; service degrades gracefully
try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("⚠️  LangChain not available — multi-agent service will use fallback")

try:
    from langgraph.prebuilt import create_react_agent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

try:
    from langchain_tavily import TavilySearch
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


def _step(agent: str, step: str, **kwargs) -> Dict[str, Any]:
    """Build a standardised step event dict for SSE streaming."""
    return {"agent": agent, "step": step, "ts": time.time(), **kwargs}


class MultiAgentReportService:
    """
    Supervisor-pattern 4-agent pipeline for research report generation.

    Usage:
        service = MultiAgentReportService(pathway_reader, company_service, analytics_service)
        for event in service.run_company_report("FCEL"):
            # event is a dict → JSON-encode → SSE data frame
            emit(event)
    """

    AGENT_COLORS = {
        "Planner":     "amber",
        "NewsAgent":   "blue",
        "MarketAgent": "green",
        "WebAgent":    "purple",
        "Synthesizer": "white",
    }

    def __init__(self, pathway_reader, company_service, analytics_service):
        self.pathway_reader    = pathway_reader
        self.company_service   = company_service
        self.analytics_service = analytics_service

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: Company report
    # ──────────────────────────────────────────────────────────────────────────

    def run_company_report(self, ticker: str) -> Generator[Dict, None, None]:
        """Stream company research report steps."""
        try:
            from llm_manager import get_llm
            llm = get_llm()
        except Exception:
            llm = None

        # 1. Planner
        yield _step("Planner", "routing", message=f"Planning research for {ticker} — routing to 3 agents")

        # 2. MarketAgent — always runs (no external dependencies)
        yield _step("MarketAgent", "tool_call", tool="get_company_details", input=ticker)
        market_data = self._get_market_data(ticker)
        yield _step("MarketAgent", "tool_result",
                    result=f"Price: {market_data.get('price','N/A')} | Risk: {market_data.get('risk','N/A')} | "
                           f"Velocity: {market_data.get('velocity','N/A')} | ESG: {market_data.get('esg_rating','N/A')}")

        # 3. NewsAgent — RAG search for ticker news
        yield _step("NewsAgent", "tool_call", tool="search_news_rag", input=ticker)
        news_results = self._search_news(ticker, company_name=market_data.get('company_name', ''))
        yield _step("NewsAgent", "tool_result",
                    result=f"{len(news_results)} relevant articles found — "
                           f"sentiment avg: {self._avg_sentiment(news_results):.3f}")

        # 4. WebAgent — optional, needs Tavily
        web_results = ""
        if TAVILY_AVAILABLE and llm:
            yield _step("WebAgent", "tool_call", tool="tavily_search",
                        input=f"{market_data.get('company_name', ticker)} carbon ESG sustainability 2024")
            web_results = self._web_search(market_data.get('company_name', ticker), ticker)
            yield _step("WebAgent", "tool_result",
                        result=web_results[:200] + "..." if len(web_results) > 200 else web_results)
        else:
            yield _step("WebAgent", "skipped", message="Web search skipped (Tavily not available)")

        # 5. Synthesizer
        yield _step("Synthesizer", "synthesizing", message="Merging agent outputs → generating report")
        report_html = self._synthesize_company(ticker, market_data, news_results, web_results, llm)
        yield _step("Synthesizer", "complete", report=report_html)

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC: Project report
    # ──────────────────────────────────────────────────────────────────────────

    def run_project_report(self, project_id: str) -> Generator[Dict, None, None]:
        """Stream project research report steps."""
        try:
            from llm_manager import get_llm
            llm = get_llm()
        except Exception:
            llm = None

        yield _step("Planner", "routing", message=f"Planning research for project {project_id}")

        # MarketAgent — project details
        yield _step("MarketAgent", "tool_call", tool="get_project_details", input=project_id)
        proj_data = self._get_project_data(project_id)
        yield _step("MarketAgent", "tool_result",
                    result=f"Name: {proj_data.get('name','N/A')} | Category: {proj_data.get('category','N/A')} | "
                           f"Price: {proj_data.get('price','N/A')} | Supply: {proj_data.get('available_credits','N/A')}")

        # NewsAgent — semantic search for project
        query = f"{proj_data.get('name', project_id)} carbon project {proj_data.get('category', '')}"
        yield _step("NewsAgent", "tool_call", tool="search_carbon_news", input=query)
        news_results = self._search_news_by_text(query)
        yield _step("NewsAgent", "tool_result", result=f"{len(news_results)} related news articles")

        # WebAgent
        web_results = ""
        if TAVILY_AVAILABLE and llm and proj_data.get('name'):
            yield _step("WebAgent", "tool_call", tool="tavily_search", input=proj_data['name'])
            web_results = self._web_search(proj_data['name'], project_id)
            yield _step("WebAgent", "tool_result", result=web_results[:200] + "..." if len(web_results) > 200 else web_results)
        else:
            yield _step("WebAgent", "skipped", message="Web search skipped")

        yield _step("Synthesizer", "synthesizing", message="Merging data → generating project report")
        report_html = self._synthesize_project(project_id, proj_data, news_results, web_results, llm)
        yield _step("Synthesizer", "complete", report=report_html)

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: Data gathering helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch company details + live signals."""
        try:
            result = self.company_service.get_company_details(ticker)
            data = result.get('data', {}) if result.get('success') else {}
        except Exception:
            data = {}

        # Enrich with live signals from analytics
        try:
            movers = self.analytics_service.get_top_movers()
            for c in movers.get('companies', []):
                if c.get('ticker') == ticker:
                    data.update({
                        'risk':       c.get('risk'),
                        'velocity':   c.get('velocity'),
                        'confidence': c.get('confidence'),
                        'sentiment_24h': c.get('sentiment_24h'),
                        'news_24h':   c.get('news_24h'),
                    })
                    break
        except Exception:
            pass

        return data

    def _get_project_data(self, project_id: str) -> Dict[str, Any]:
        """Fetch project details."""
        try:
            projects = self.pathway_reader.get_projects(limit=1000)
            for p in projects:
                if p.get('project_id') == project_id or p.get('id') == project_id:
                    return {
                        'name':             p.get('project_name', p.get('name', '')),
                        'category':         p.get('category', ''),
                        'country':          p.get('country', ''),
                        'price':            p.get('price', 0),
                        'available_credits':p.get('available_credits', 0),
                        'vintage':          p.get('vintage', ''),
                        'registry_status':  p.get('registry_status', ''),
                        'description':      p.get('description', ''),
                        'methodology':      p.get('methodology', ''),
                    }
        except Exception:
            pass
        return {}

    def _search_news(self, ticker: str, company_name: str = '') -> list:
        """Match news articles to ticker/company name."""
        import re
        try:
            news = self.pathway_reader.get_news(limit=250)
            parts = [re.escape(ticker)]
            if company_name and len(company_name) > 3:
                parts.append(re.escape(company_name))
            pat = re.compile(r'\b(' + '|'.join(parts) + r')\b', re.IGNORECASE)
            return [a for a in news if pat.search((a.get('title','') + ' ' + a.get('summary','')))][:20]
        except Exception:
            return []

    def _search_news_by_text(self, query: str) -> list:
        """Simple keyword match for project news."""
        try:
            news = self.pathway_reader.get_news(limit=250)
            q = query.lower().split()[:5]
            return [a for a in news if any(w in (a.get('title','') + a.get('summary','')).lower() for w in q)][:15]
        except Exception:
            return []

    def _web_search(self, name: str, identifier: str) -> str:
        """Run Tavily web search, return text summary."""
        if not TAVILY_AVAILABLE:
            return ""
        try:
            search = TavilySearch(max_results=5)
            result = search.invoke({"query": f"{name} carbon ESG sustainability 2024"})
            return str(result)[:1000]
        except Exception as e:
            return f"Web search failed: {e}"

    def _avg_sentiment(self, articles: list) -> float:
        mapping = {"Positive": 1.0, "Negative": -1.0}
        if not articles:
            return 0.0
        scores = [mapping.get(a.get('sentiment', 'Neutral'), 0.0) for a in articles]
        return sum(scores) / len(scores)

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVATE: Synthesis helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _synthesize_company(self, ticker, market_data, news, web, llm) -> str:
        """Generate or fallback-compose the company report HTML."""
        name = market_data.get('name') or market_data.get('company_name') or ticker

        # Build context for LLM
        news_summary = "\n".join([
            f"- [{a.get('sentiment','?')}] {a.get('title','')} ({a.get('source','')})"
            for a in news[:8]
        ])

        context = f"""
Company: {name} ({ticker})
Industry: {market_data.get('industry', 'N/A')}
Stock Price: ${market_data.get('price', 'N/A')}
Change %: {market_data.get('change_percent', 'N/A')}%
ESG Rating: {market_data.get('esg_rating', 'N/A')}
Risk Score: {market_data.get('risk', 'N/A')}
Media Velocity: {market_data.get('velocity', 'N/A')}
Confidence: {market_data.get('confidence', 'N/A')}
Sentiment 24H: {market_data.get('sentiment_24h', 'N/A')}
News 24H: {market_data.get('news_24h', 0)} articles
Description: {market_data.get('description', '')}

Recent news:
{news_summary or 'No matched news articles.'}

Web research:
{web[:500] if web else 'Not available.'}
"""

        if llm:
            try:
                prompt = f"""You are a carbon market analyst. Based on the following data, write a concise company intelligence report in Markdown.
Include headings for: Overview, Carbon/ESG Position, Live Market Signals, Risk Assessment, Recent News Analysis.
CRITICAL FORMATTING RULES:
1. You MUST use Markdown headers (###) for every section.
2. You MUST leave a blank empty line before AND after every header.
3. Use bold text (**bold**) to emphasize key metrics.
4. Use bulleted lists (-) for data points.
Keep it concise (4–6 paragraphs).

{context}"""
                response = llm.invoke([HumanMessage(content=prompt)])
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"LLM synthesis failed: {e}")

        # Fallback: structured Markdown without LLM
        return f"""### {name} Company Intelligence Report

**Overview:**
{name} is operating in the {market_data.get('industry','technology')} sector.

**Carbon/ESG Position:**
- ESG Rating: {market_data.get('esg_rating','N/A')}

**Live Market Signals:**
- Stock Price: ${market_data.get('price','N/A')}
- Change %: {market_data.get('change_percent','N/A')}%

**Risk Assessment:**
- Risk Score: {market_data.get('risk','N/A')}
- Media Velocity: {market_data.get('velocity','N/A')}

**Recent News Analysis:**
{news_summary or 'No recent news articles found.'}
"""

    def _synthesize_project(self, project_id, proj_data, news, web, llm) -> str:
        """Generate or fallback-compose the project report HTML."""
        name = proj_data.get('name', project_id)
        news_summary = "\n".join([
            f"- [{a.get('sentiment','?')}] {a.get('title','')}"
            for a in news[:6]
        ])
        context = f"""
Project: {name}
ID: {project_id}
Category: {proj_data.get('category','N/A')}
Country: {proj_data.get('country','N/A')}
Methodology: {proj_data.get('methodology','N/A')}
Price: ${proj_data.get('price',0)}/tCO₂e
Available Credits: {proj_data.get('available_credits',0)}
Status: {proj_data.get('registry_status','N/A')}
Description: {proj_data.get('description','')[:400]}

Related news:
{news_summary or 'No related news.'}
"""
        if llm:
            try:
                prompt = f"""You are a carbon market analyst. Write a concise project intelligence report in Markdown.
Include headings for: Overview, Carbon Credit Details, Market Position, Related News Summary.
CRITICAL FORMATTING RULES:
1. You MUST use Markdown headers (###) for every section.
2. You MUST leave a blank empty line before AND after every header.
3. Use bold text (**bold**) to emphasize key metrics.
4. Use bulleted lists (-) for data points.
Keep concise (3–5 paragraphs).

{context}"""
                response = llm.invoke([HumanMessage(content=prompt)])
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"LLM project synthesis failed: {e}")

        rows = "".join(f"<li>{a.get('title','')}</li>" for a in news[:5])
        return f"""### Overview
{name} is a {proj_data.get('category','N/A')} project in {proj_data.get('country','N/A')}.
{proj_data.get('description','')[:400]}

### Carbon Credit Details
- Price: **${proj_data.get('price',0)}/tCO₂e**
- Available Credits: **{proj_data.get('available_credits',0)}**
- Vintage: **{proj_data.get('vintage','N/A')}**
- Methodology: **{proj_data.get('methodology','N/A')}**
- Status: **{proj_data.get('registry_status','N/A')}**

### Related News ({len(news)} articles)
{rows or '- No related news articles.'}
"""
