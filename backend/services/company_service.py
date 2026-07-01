"""
Company Service - Detailed company information and reports

Frontend Feature: ReportPage - Company Detail View
Endpoints: GET /api/company/:ticker, GET /api/company/:ticker/insights, GET /api/company/:ticker/future-impact
"""

import os
import logging
from typing import Dict, List, Any, Optional
from llm_manager import get_llm
import markdown

logger = logging.getLogger(__name__)

# Try to import LangChain
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_tavily import TavilySearch
    from langgraph.prebuilt import create_react_agent
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("⚠️ LangChain or Tavily not installed. Using fallback analysis.")


class CompanyService:
    """Service for detailed company information"""
    
    def __init__(self, pathway_reader):
        """Initialize Company Service"""
        self.pathway_reader = pathway_reader
        logger.info("✅ Company Service initialized")

    def _fallback_response(self, company: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Return a deterministic non-AI response when Gemini/Tavily are unavailable."""
        name = company.get('name', '')
        ticker = company.get('ticker', '')
        industry = company.get('industry', 'Unknown')
        description = company.get('description', '').strip()
        market_cap = company.get('market_cap', 'N/A')
        esg_rating = company.get('esg_rating', 'N/A')
        gii_score = company.get('gii_score', 0)

        if analysis_type == 'insights':
            fallback_text = f"""OVERVIEW:
{name} ({ticker}) operates in the {industry} sector.
{description or 'No detailed description is currently available from the database.'}

SUSTAINABILITY POSITION:
ESG rating: {esg_rating}. Green Innovation Score: {gii_score}/100. Market cap: {market_cap}.
Add GOOGLE_API_KEY and TAVILY_API_KEY to enable AI-powered web research and richer sustainability analysis."""
        else:
            fallback_text = f"""OVERVIEW:
{name} ({ticker}) is a {industry} company with the following available data: {description or 'No detailed company description is available yet.'}

FUTURE IMPACT:
The local backend is running without Gemini/Tavily, so this is a data-only summary. ESG rating: {esg_rating}, Green Innovation Score: {gii_score}/100, Market cap: {market_cap}.
Add GOOGLE_API_KEY and TAVILY_API_KEY to enable the full AI-driven future impact workflow."""

        return {
            'success': True,
            'data': {
                'ticker': ticker,
                'company_name': name,
                'insights' if analysis_type == 'insights' else 'analysis': markdown.markdown(fallback_text, extensions=['nl2br', 'sane_lists'])
            }
        }
    
    # ============================================================================
    # API ENDPOINT: /api/company/<ticker>
    # ============================================================================

    def get_company_details(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive company details for report page
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Dict with complete company information
        """
        try:
            finance_data = self.pathway_reader.get_finance(ticker=ticker)
            
            if not finance_data or len(finance_data) == 0:
                return {'success': False, 'error': f'Company {ticker} not found'}
            
            company = finance_data[0]
            
            # Use 'price' field as the source of truth, since 'stock_price' is often null in data
            price_value = company.get('price', 0) or company.get('stock_price', 0)
            
            return {
                'success': True,
                'data': {
                    'id': company.get('ticker', ''),
                    'ticker': company.get('ticker', ''),
                    'name': company.get('company_name', ''),
                    'company_name': company.get('company_name', ''),
                    'industry': company.get('industry', ''),
                    'description': company.get('description', ''),
                    'website': company.get('website', ''),
                    
                    # Financial metrics - price is the actual field in finance.jsonl
                    'stock_price': price_value,  # Frontend uses stock_price
                    'price': price_value,
                    'market_cap': company.get('market_cap', ''),
                    'volume': company.get('volume', None),
                    'change_percent': company.get('change_percent', 0),
                    
                    # ESG metrics
                    'esg_rating': company.get('esg_rating', 'N/A'),
                    'gii_score': company.get('gii_score', 0),
                    'sustainability_update': company.get('sustainability_update', ''),
                    
                    # Timestamp
                    'timestamp': company.get('time', 0),
                    'time': company.get('time', 0),
                    'last_updated': company.get('time', 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting company details for {ticker}: {e}")
            return {'success': False, 'error': str(e)}
    
    # ============================================================================
    # API ENDPOINT: /api/company/<ticker>/insights
    # ============================================================================
    def get_company_insights(self, ticker: str) -> Dict[str, Any]:
        """
        Get general AI-powered insights using Tavily search agent
        Returns comprehensive analysis with web research
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Dict with insights text
        """
        try:
            company_data = self.get_company_details(ticker)
            
            if not company_data.get('success'):
                return company_data
            
            company = company_data['data']
            
            # Prepare company info
            name = company.get('name', '')
            industry = company.get('industry', '')
            description = company.get('description', '')
            market_cap = company.get('market_cap', 'N/A')
            esg_rating = company.get('esg_rating', 'N/A')
            gii_score = company.get('gii_score', 0)

            if not LANGCHAIN_AVAILABLE or not os.getenv('GOOGLE_API_KEY') or not os.getenv('TAVILY_API_KEY'):
                return self._fallback_response(company, 'insights')
            
            # Use LangChain + Tavily agent to generate insights with web search
            llm = get_llm()

            if not llm:
                return self._fallback_response(company, 'insights')
            
            logger.info(f"🔍 Creating Tavily search agent for {name}...")
            
            # Create Tavily search tool
            search = TavilySearch(
                max_results=10           # Get more sources for analysis
            )
            
            # Create agent with simple system prompt
            system_prompt = f"""You are a sustainability analyst. Given company information, research and provide insights.

Company to analyze: {name} ({ticker})
Industry: {industry}
Current ESG Rating: {esg_rating}
Green Innovation Score: {gii_score}/100
Market Cap: {market_cap}

Search online for basic information about what the company does.
Look for anything related to the company's sustainability efforts, carbon reduction initiatives, net-zero goals, or involvement in carbon credits.
Provide a short, clear summary based on publicly available information.

Output Format:

OVERVIEW:
1–2 sentence summary of what the company does.

SUSTAINABILITY POSITION:
1–2 sentences on how the company aligns with sustainability, green initiatives, or carbon credit efforts.

Keep the response concise."""

            agent = create_react_agent(
                model=llm,
                tools=[search],
                prompt=system_prompt
            )

            # Run agent analysis
            logger.info(f"🤖 Running agent for {name}...")
            result = agent.invoke({
                "messages": [{"role": "user", "content": f"Research and analyze {name} ({ticker})"}]
            })
                                
            # Extract the final response - handle multimodal content
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                content = last_message.content
                # If content is a list (multimodal), extract only text parts
                if isinstance(content, list):
                    text_parts = [item.get('text', '') if isinstance(item, dict) else str(item) 
                                  for item in content if isinstance(item, dict) and item.get('type') == 'text']
                    insights_text = ' '.join(text_parts).strip()
                else:
                    insights_text = str(content).strip()
            else:
                insights_text = str(last_message)
            
            # Convert markdown to HTML for proper formatting
            insights_html = markdown.markdown(insights_text, extensions=['nl2br', 'sane_lists'])
                    
            logger.info(f"✅ Agent insights generated for {name}")
                    
            return {
                'success': True,
                'data': {
                    'ticker': ticker,
                    'company_name': name,
                    'insights': insights_html
                }
            }
        except Exception as e:
            logger.error(f"Error generating insights for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
                   
    
    # ============================================================================
    # API ENDPOINT: /api/company/<ticker>/future-impact
    # ============================================================================
    def get_future_impact_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Get sustainability and future impact analysis for the company
        Uses AI agent with multiple tools: web search, news RAG, projects RAG, company info
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Dict with future impact analysis text
        """
        company_data = self.get_company_details(ticker)
        
        if not company_data.get('success'):
            return company_data
        
        company = company_data['data']
        name = company.get('name', '')
        industry = company.get('industry', '')
        ticker_symbol = company.get('ticker', '')
        
        # Get LLM
        llm = get_llm()

        if not LANGCHAIN_AVAILABLE or not llm or not os.getenv('GOOGLE_API_KEY') or not os.getenv('TAVILY_API_KEY'):
            return self._fallback_response(company, 'future_impact')
        
        # Import RAG services
        from services.news_rag_service import search_news
        from services.projects_rag_service import search_projects
        
        # Store reference to avoid closure issues
        get_details = self.get_company_details
        
        # Define custom tools for the agent
        @tool
        def search_news_rag(query: str, k: int = 5) -> str:
            """Search carbon/ESG news articles using RAG. Returns relevant news chunks about sustainability, carbon markets, ESG trends."""
            try:
                results = search_news(query, k=k)
                if not results:
                    return "No news articles found."
                
                output = []
                for i, chunk in enumerate(results, 1):
                    output.append(f"\n--- News {i} ---")
                    output.append(f"Title: {chunk['title']}")
                    output.append(f"Source: {chunk['source']}")
                    output.append(f"Link: {chunk['link']}")
                    output.append(f"Content: {chunk['content'][:300]}...")
                return "\n".join(output)
            except Exception as e:
                return f"Error searching news: {str(e)}"
        
        @tool
        def search_projects_rag(query: str, k: int = 5) -> str:
            """Search carbon credit projects using RAG. Returns relevant projects about renewable energy, REDD+, carbon offsets, etc."""
            try:
                results = search_projects(query, k=k)
                if not results:
                    return "No projects found."
                
                output = []
                for i, chunk in enumerate(results, 1):
                    output.append(f"\n--- Project {i} ---")
                    output.append(f"Name: {chunk['name']}")
                    output.append(f"Registry: {chunk['registry']}")
                    output.append(f"Country: {chunk['country']}")
                    output.append(f"Type: {chunk['type']}")
                    output.append(f"Link: {chunk['registry_link']}")
                    output.append(f"Content: {chunk['content'][:300]}...")
                return "\n".join(output)
            except Exception as e:
                return f"Error searching projects: {str(e)}"
        
        @tool
        def get_company_info(ticker_input: str) -> str:
            """Get detailed information about a company including stock price, ESG rating, GII score, industry, description."""
            try:
                comp_data = get_details(ticker_input)
                if not comp_data.get('success'):
                    return f"Company {ticker_input} not found."
                
                comp = comp_data['data']
                info = f"""
Company: {comp.get('name', '')}
Ticker: {comp.get('ticker', '')}
Industry: {comp.get('industry', '')}
Stock Price: ${comp.get('stock_price', 0)}
Market Cap: {comp.get('market_cap', 'N/A')}
ESG Rating: {comp.get('esg_rating', 'N/A')}
Green Innovation Index: {comp.get('gii_score', 0)}/100
Description: {comp.get('description', '')}
Website: {comp.get('website', '')}
"""
                return info.strip()
            except Exception as e:
                return f"Error getting company info: {str(e)}"
        
        # Create Tavily search tool
        search = TavilySearch(
            max_results=10
        )
        
        # Create agent with all tools
        tools = [search, search_news_rag, search_projects_rag, get_company_info]
        
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt="""You are a Sustainability and Market Impact Analyst AI Agent. You have four tools: (1) news RAG, (2) carbon-projects RAG, (3) internet search, (4) company info.

For any company, use every tool multiple times. Always start with broad queries, not just the company name. Add sector and product keywords. Example: if the company is Tesla, also search “EV”, “electric vehicles”, “cars”, “battery manufacturing”, “autonomous driving”, “solar”, etc. Apply the same logic to any company based on its industry.

Use the news RAG and carbon RAG with several wide queries covering sustainability, ESG, carbon credits, climate targets, regulatory exposure, controversies, and sector trends. Use internet search and company info to gather official filings, sustainability reports, and verified data.

After collecting information, create a short report:

1–2 sentence company overview

How the company aligns with sustainability (verified actions only)

Relevant government policies affecting it

Important recent news and its impact

How these factors may influence future stock price (mark as speculative)

If data is missing or unverified, state that clearly. Keep the output concise."""
        )
        
        # Invoke agent with company name
        logger.info(f"🤖 Running future impact agent for {name}...")
        result = agent.invoke({
            "messages": [{"role": "user", "content": f"Analyze the sustainability and future impact of {name} ({ticker_symbol}) in the {industry} industry. Provide comprehensive analysis covering environmental impact, regulatory compliance, carbon footprint, green initiatives, and future growth projections."}]
        })
        
        # Extract response - handle multimodal content
        last_message = result["messages"][-1]
        if hasattr(last_message, 'content'):
            content = last_message.content
            # If content is a list (multimodal), extract only text parts
            if isinstance(content, list):
                text_parts = [item.get('text', '') if isinstance(item, dict) else str(item) 
                              for item in content if isinstance(item, dict) and item.get('type') == 'text']
                analysis_text = ' '.join(text_parts).strip()
            else:
                analysis_text = str(content).strip()
        else:
            analysis_text = str(last_message)
        
        # Convert markdown to HTML for proper formatting
        analysis_html = markdown.markdown(analysis_text, extensions=['nl2br', 'sane_lists'])
        
        logger.info(f"✅ Future impact analysis generated for {name}")
        
        return {
            'success': True,
            'data': {
                'ticker': ticker,
                'company_name': name,
                'analysis': analysis_html
            }
        }
    
    # ============================================================================
    # API ENDPOINT: /api/company/<ticker>/custom-query
    # ============================================================================
    def custom_query(self, ticker: str, query: str) -> Dict[str, Any]:
        """
        Answer custom questions about the company using AI agent with conversation memory
        
        Args:
            ticker: Company ticker symbol
            query: User's question about the company
            
        Returns:
            Dict with answer to the query
        """
        company_data = self.get_company_details(ticker)
        
        if not company_data.get('success'):
            return company_data
        
        company = company_data['data']
        name = company.get('name', '')
        industry = company.get('industry', '')
        
        # Get LLM
        llm = get_llm()

        if not LANGCHAIN_AVAILABLE or not llm or not os.getenv('GOOGLE_API_KEY') or not os.getenv('TAVILY_API_KEY'):
            return jsonify({
                'success': False,
                'error': 'AI chat is not configured yet. Add GOOGLE_API_KEY and TAVILY_API_KEY to enable it.'
            }), 503
        
        # Import RAG services
        from services.news_rag_service import search_news
        from services.projects_rag_service import search_projects
        
        # Store reference to avoid closure issues
        get_details = self.get_company_details
        
        # Define custom tools for the agent (same as future impact)
        @tool
        def search_news_rag(query: str, k: int = 5) -> str:
            """Search carbon/ESG news articles using RAG. Returns relevant news chunks about sustainability, carbon markets, ESG trends."""
            try:
                results = search_news(query, k=k)
                if not results:
                    return "No news articles found."
                
                output = []
                for i, chunk in enumerate(results, 1):
                    output.append(f"\n--- News {i} ---")
                    output.append(f"Title: {chunk['title']}")
                    output.append(f"Source: {chunk['source']}")
                    output.append(f"Link: {chunk['link']}")
                    output.append(f"Content: {chunk['content'][:300]}...")
                return "\n".join(output)
            except Exception as e:
                return f"Error searching news: {str(e)}"
        
        @tool
        def search_projects_rag(query: str, k: int = 5) -> str:
            """Search carbon credit projects using RAG. Returns relevant projects about renewable energy, REDD+, carbon offsets, etc."""
            try:
                results = search_projects(query, k=k)
                if not results:
                    return "No projects found."
                
                output = []
                for i, chunk in enumerate(results, 1):
                    output.append(f"\n--- Project {i} ---")
                    output.append(f"Name: {chunk['name']}")
                    output.append(f"Registry: {chunk['registry']}")
                    output.append(f"Country: {chunk['country']}")
                    output.append(f"Type: {chunk['type']}")
                    output.append(f"Link: {chunk['registry_link']}")
                    output.append(f"Content: {chunk['content'][:300]}...")
                return "\n".join(output)
            except Exception as e:
                return f"Error searching projects: {str(e)}"
        
        @tool
        def get_company_info(ticker_input: str) -> str:
            """Get detailed information about a company including stock price, ESG rating, GII score, industry, description."""
            try:
                comp_data = get_details(ticker_input)
                if not comp_data.get('success'):
                    return f"Company {ticker_input} not found."
                
                comp = comp_data['data']
                info = f"""
Company: {comp.get('name', '')}
Ticker: {comp.get('ticker', '')}
Industry: {comp.get('industry', '')}
Stock Price: ${comp.get('stock_price', 0)}
Market Cap: {comp.get('market_cap', 'N/A')}
ESG Rating: {comp.get('esg_rating', 'N/A')}
Green Innovation Index: {comp.get('gii_score', 0)}/100
Description: {comp.get('description', '')}
Website: {comp.get('website', '')}
"""
                return info.strip()
            except Exception as e:
                return f"Error getting company info: {str(e)}"
        
        # Create Tavily search tool
        search = TavilySearch(
            max_results=10
        )
        
        # Create agent with all tools and built-in memory
        tools = [search, search_news_rag, search_projects_rag, get_company_info]
        
        # MemorySaver provides thread-local conversation persistence
        checkpointer = MemorySaver()
        
        
        # Message limits are handled differently in ReactAgent, or we can just pass the modifier
        # For simplicity, we just use the system prompt
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=f"""You are a Sustainability Insights Assistant AI Agent analyzing {name} ({ticker}), a company in the {industry} industry.

CURRENT COMPANY CONTEXT:
- Company: {name}
- Ticker: {ticker}
- Industry: {industry}

You can chat freely with the user and assist with any custom request about THIS COMPANY related to sustainability, carbon markets, policy impacts, or stock implications. 

You have access to: (1) news RAG, (2) carbon-projects RAG, (3) internet search, and (4) company info tool.

When the user asks questions, they are asking about {name}. Use the get_company_info tool with ticker "{ticker}" to get current data about {name}.

When researching, use broad queries with sector and product keywords (e.g., for Tesla → EVs, batteries, cars, autonomy). Use each tool multiple times if needed.

Provide clear, concise answers. Structure responses according to the user's request. If information is missing or unverified, state it clearly. Keep responses accurate, helpful, and grounded in tool results.

Remember: All questions are about {name} ({ticker}) unless the user explicitly asks about a different company.""",
            checkpointer=checkpointer
        )
        
        # Use thread_id for conversation memory
        config = {"configurable": {"thread_id": ticker}}
        
        # Invoke agent with conversation history (memory persists automatically)
        logger.info(f"🤖 Running chat agent for {name} with query: {query}")
        result = agent.invoke(
            {"messages": [HumanMessage(content=query)]},
            config
        )
        
        # Extract response - handle multimodal content
        last_message = result["messages"][-1]
        if hasattr(last_message, 'content'):
            content = last_message.content
            # If content is a list (multimodal), extract only text parts
            if isinstance(content, list):
                text_parts = [item.get('text', '') if isinstance(item, dict) else str(item) 
                              for item in content if isinstance(item, dict) and item.get('type') == 'text']
                answer = ' '.join(text_parts).strip()
            else:
                answer = str(content).strip()
        else:
            answer = str(last_message)
        
        # Convert markdown to HTML for proper formatting
        answer_html = markdown.markdown(answer, extensions=['nl2br', 'sane_lists'])
        
        logger.info(f"✅ Chat response generated for {name}")
        
        return {
            'success': True,
            'data': {
                'ticker': ticker,
                'company_name': name,
                'query': query,
                'answer': answer_html
            }
        }
