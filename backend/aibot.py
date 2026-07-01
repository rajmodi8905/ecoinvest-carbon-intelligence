"""
AI Chatbot Service - LangChain Agent with Tool Calling

A LangChain agent that can call tools to perform frontend actions using Google Gemini.
Uses the modern create_agent API for production-ready agent implementation.
"""

from flask import Blueprint, request, jsonify
import logging
import os
import markdown

try:
    from langgraph.prebuilt import create_react_agent
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import MemorySaver
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

    def tool(func=None, **kwargs):
        if func is None:
            def decorator(inner_func):
                return inner_func

            return decorator
        return func

    create_react_agent = None
    MemorySaver = None

import frontend_actions
from llm_manager import get_llm

# Try to import Tavily for web search
try:
    from langchain_tavily import TavilySearch
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("⚠️ Tavily not available - web search disabled")

# Import RAG and Service modules
try:
    from services.news_rag_service import search_news
    NEWS_RAG_AVAILABLE = True
except ImportError:
    NEWS_RAG_AVAILABLE = False
    print("⚠️ News RAG service not available")

# References to services (set by app.py)
_company_service = None
_project_service = None
_projects_service = None
_live_news_service = None

def set_company_service(service):
    """Set the company service reference from app.py"""
    global _company_service
    _company_service = service
    logger.info("✅ Company service connected to aibot")

def set_project_service(service):
    """Set the project service reference from app.py"""
    global _project_service
    _project_service = service
    logger.info("✅ Project service connected to aibot")

def set_projects_service(service):
    """Set the projects service reference from app.py"""
    global _projects_service
    _projects_service = service
    logger.info("✅ Projects service connected to aibot")

def set_live_news_service(service):
    """Set the live news service reference from app.py"""
    global _live_news_service
    _live_news_service = service
    logger.info("✅ Live News service connected to aibot")

# Set Google API Key
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")  # Use env variable or empty if not set

logger = logging.getLogger(__name__)

# Create Blueprint for chatbot routes
aibot_bp = Blueprint('aibot', __name__)

# Chat history storage
chat_histories = {}

# Reference to pathway_reader (set by app.py)
_pathway_reader = None

def set_pathway_reader(reader):
    """Set the pathway reader reference from app.py"""
    global _pathway_reader
    _pathway_reader = reader
    logger.info("✅ Pathway reader connected to aibot")

def resolve_ticker(company_input: str) -> tuple:
    """
    Resolve company name or ticker to (company_name, ticker).
    Searches the actual finance data from PathwayDataReader.
    
    Args:
        company_input: Either a company name (e.g., 'Tesla') or ticker (e.g., 'TSLA')
        
    Returns:
        Tuple of (company_name, ticker) or (input, input) if not found
    """
    if not _pathway_reader:
        logger.warning("⚠️ No pathway reader available for company lookup")
        return (company_input, company_input.upper())
    
    try:
        finance_data = _pathway_reader.get_finance()
        input_lower = company_input.lower().strip()
        
        # First, try exact ticker match
        for company in finance_data:
            ticker = company.get('ticker', '')
            if ticker.lower() == input_lower:
                name = company.get('company_name', ticker)
                logger.info(f"🔍 Resolved '{company_input}' to ticker: {ticker}")
                return (name, ticker)
        
        # Second, try exact company name match
        for company in finance_data:
            name = company.get('company_name', '')
            if name.lower() == input_lower:
                ticker = company.get('ticker', name)
                logger.info(f"🔍 Resolved '{company_input}' to ticker: {ticker}")
                return (name, ticker)
        
        # Third, try partial name match (company name contains input)
        for company in finance_data:
            name = company.get('company_name', '')
            if input_lower in name.lower():
                ticker = company.get('ticker', name)
                logger.info(f"🔍 Fuzzy matched '{company_input}' to {name} ({ticker})")
                return (name, ticker)
        
        # Fourth, try partial name match (input contains company name)
        for company in finance_data:
            name = company.get('company_name', '')
            if name.lower() and name.lower() in input_lower:
                ticker = company.get('ticker', name)
                logger.info(f"🔍 Fuzzy matched '{company_input}' to {name} ({ticker})")
                return (name, ticker)
        
        # Not found - return as-is with uppercased ticker
        logger.info(f"⚠️ Could not resolve '{company_input}', using as-is")
        return (company_input, company_input.upper())
        
    except Exception as e:
        logger.error(f"Error resolving company: {e}")
        return (company_input, company_input.upper())

# ============================================================================
# DEFINE TOOLS
# ============================================================================

@tool
def change_theme() -> str:
    """Toggle the theme between light and dark mode."""
    success = frontend_actions.change_theme()
    return "Theme changed successfully!" if success else "Failed to change theme."

@tool
def list_available_companies() -> str:
    """List all companies available in the database with their tickers.
    
    Returns:
        A list of all available companies
    """
    if not _pathway_reader:
        return "Company data is currently unavailable."
    
    try:
        finance_data = _pathway_reader.get_finance()
        companies = []
        for company in finance_data:
            ticker = company.get('ticker', '')
            name = company.get('company_name', ticker)
            esg = company.get('esg_rating', 'N/A')
            companies.append(f"• {name} ({ticker}) - ESG: {esg}")
        
        if companies:
            return "Available companies:\n" + "\n".join(companies)
        return "No companies found in database."
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        return "Error retrieving company list."

@tool
def get_watchlist() -> str:
    """Get the current companies in the user's watchlist.
    
    Returns:
        A formatted list of companies currently in the user's watchlist with their details
    """
    try:
        # Get current watchlist state
        watchlist = frontend_actions.get_current_watchlist()
        
        if not watchlist:
            return "Watchlist is empty (0 companies)."
        
        output = [f"Your watchlist ({len(watchlist)} companies):\n"]
        for i, company in enumerate(watchlist, 1):
            name = company.get('name') or company.get('company_name', 'N/A')
            ticker = company.get('ticker') or company.get('id', 'N/A')
            industry = company.get('industry', 'N/A')
            esg = company.get('esg_rating') or company.get('esg_score', 'N/A')
            
            output.append(f"{i}. {name} ({ticker})")
            output.append(f"   Industry: {industry}")
            output.append(f"   ESG Rating: {esg}")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        return "Error retrieving watchlist. Please try again."

@tool
def add_to_watchlist(company_name: str) -> str:
    """Add a company to the watchlist.
    
    Args:
        company_name: Name of the company (e.g., 'Tesla', 'Apple') or ticker (e.g., 'TSLA', 'AAPL')
    """
    # Resolve company name to ticker using actual finance data
    name, ticker = resolve_ticker(company_name)
    success = frontend_actions.add_company_to_watchlist(name, ticker)
    return f"Added {name} ({ticker}) to watchlist!" if success else f"Failed to add {company_name}."

@tool
def remove_from_watchlist(company_name: str) -> str:
    """Remove a company from the watchlist.
    
    Args:
        company_name: Name of the company or ticker to remove
    """
    # Resolve company name to ticker
    name, ticker = resolve_ticker(company_name)
    success = frontend_actions.remove_company_from_watchlist(ticker)
    return f"Removed {name} ({ticker}) from watchlist!" if success else f"Failed to remove {company_name}."

@tool
def go_to_detail_page(identifier: str, page_type: str = "auto") -> str:
    """Navigate to a detailed page for a company or carbon project.
    
    Args:
        identifier: Company name/ticker (e.g., 'Tesla', 'TSLA') OR project code/ID (e.g., 'VCS191', '3519')
        page_type: Type of page - 'company', 'project', or 'auto' (default: auto-detect)
    
    Returns:
        Success message or error
    """
    try:
        # Auto-detect if not specified
        if page_type == "auto":
            # Try to detect if it's a company or project
            # Companies usually have stock tickers (2-5 uppercase letters) or well-known names
            # Projects usually have codes like VCS191, VCS-191, or numeric IDs
            if identifier.upper().startswith('VCS') or identifier.upper().startswith('GS') or identifier.isdigit():
                page_type = "project"
            else:
                page_type = "company"
        
        if page_type == "company":
            # Resolve company name to ticker
            name, ticker = resolve_ticker(identifier)
            success = frontend_actions.go_to_company_page(name, ticker)
            return f"Navigating to {name} ({ticker})!" if success else f"Failed to navigate to company page."
        
        elif page_type == "project":
            # Navigate to project detail page using project ID
            success = frontend_actions.go_to_project_page(identifier)
            return f"Navigating to project {identifier}!" if success else f"Failed to navigate to project page."
        
        else:
            return "Invalid page_type. Use 'company', 'project', or 'auto'."
            
    except Exception as e:
        logger.error(f"Error navigating: {e}")
        return f"Error: {str(e)}"

@tool
def go_to_projects() -> str:
    """Navigate to the projects marketplace page (list of all carbon projects)."""
    success = frontend_actions.go_to_projects_page()
    return "Navigating to Projects marketplace!" if success else "Failed to navigate."

@tool
def search_carbon_news(query: str, k: int = 5) -> str:
    """Search carbon/ESG news articles using RAG. Returns relevant news about sustainability, carbon markets, ESG trends.
    
    Args:
        query: Search query (e.g., 'carbon credit trends', 'Tesla ESG news')
        k: Number of results (default 5)
    
    Returns:
        Relevant news with titles, sources, links, and content
    """
    if not NEWS_RAG_AVAILABLE:
        return "News RAG is unavailable."
    
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
            output.append(f"Published: {chunk['published']}")
            output.append(f"Content: {chunk['content'][:300]}...")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        return f"Error: {str(e)}"

@tool
def search_carbon_projects(query: str, k: int = 5) -> str:
    """Search carbon credit projects using semantic search. Returns projects about renewable energy, REDD+, carbon offsets.
    
    Args:
        query: Search query (e.g., 'wind energy projects', 'REDD+ Brazil')
        k: Number of results (default 5)
    
    Returns:
        Relevant projects with names, registries, countries, types
    """
    if not _projects_service:
        return "Projects service is unavailable."
    
    try:
        result = _projects_service.search_projects(query, limit=k)
        if not result.get('success') or not result.get('data'):
            return "No projects found."
        
        projects = result['data']
        output = []
        for i, project in enumerate(projects, 1):
            output.append(f"\n--- Project {i} ---")
            output.append(f"Name: {project.get('name', project.get('project_name', 'N/A'))}")
            output.append(f"ID: {project.get('id', project.get('project_id', 'N/A'))}")
            output.append(f"Registry: {project.get('registry', 'N/A')}")
            output.append(f"Country: {project.get('country', 'N/A')}")
            output.append(f"Category: {project.get('category', 'N/A')}")
            output.append(f"Methodology: {project.get('methodology', 'N/A')}")
            output.append(f"Price: ${project.get('price', 0)}/credit")
            output.append(f"Available: {project.get('available_credits', 0)} credits")
            desc = project.get('description', '')
            if desc:
                output.append(f"Description: {desc[:200]}...")
        
        output.append(f"\nSearch method: {result.get('method', 'unknown')}")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error searching projects: {e}")
        return f"Error: {str(e)}"

@tool
def get_detailed_company_info(company_name: str) -> str:
    """Get comprehensive company details including stock price, ESG rating, GII score, industry, description.
    
    Args:
        company_name: Company name or ticker (e.g., 'Tesla', 'TSLA')
    
    Returns:
        Detailed company information
    """
    if not _company_service:
        return "Company service unavailable."
    
    try:
        # Resolve company name to ticker
        name, ticker = resolve_ticker(company_name)
        result = _company_service.get_company_details(ticker)
        if not result.get('success'):
            return f"Company {company_name} not found."
        
        comp = result['data']
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
        return f"Error: {str(e)}"

@tool
def get_project_details(project_id: str) -> str:
    """Get carbon project details including name, country, methodology, credits, price.
    
    Args:
        project_id: Project ID
    
    Returns:
        Project details
    """
    if not _project_service:
        return "Project service unavailable."
    
    try:
        result = _project_service.get_project_details(project_id)
        if not result.get('success'):
            return f"Project {project_id} not found."
        
        proj = result['data']
        info = f"""
Project: {proj.get('name', '')}
Country: {proj.get('country', 'N/A')}
Category: {proj.get('category', 'N/A')}
Methodology: {proj.get('methodology', 'N/A')}
Available Credits: {proj.get('available_credits', 0)}
Price: ${proj.get('price', 0)}
Status: {proj.get('registry_status', 'N/A')}
Description: {proj.get('description', 'N/A')}
"""
        return info.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def search_web(query: str) -> str:
    """Search the internet for current information, news, and data using Tavily.
    
    Args:
        query: Search query (e.g., 'Tesla carbon credits 2024', 'latest ESG trends')
    
    Returns:
        Search results with sources and snippets
    """
    if not TAVILY_AVAILABLE:
        return "Web search is unavailable. Tavily not installed."
    
    try:
        search = TavilySearch(
            max_results=10
        )
        # TavilySearch.invoke returns a string directly
        results = search.invoke({"query": query})
        
        if not results:
            return "No results found."
        
        # TavilySearch returns formatted text, not structured data
        return f"Search results for: {query}\n\n{results}"
    except Exception as e:
        logger.error(f"Error searching web: {e}")
        return f"Search error: {str(e)}"

@tool
def get_live_news(limit: int = 10, source: str = None) -> str:
    """Get latest live news articles from the dashboard feed.
    
    Args:
        limit: Maximum number of articles to return (default: 10, max: 50)
        source: Filter by specific news source (optional)
    
    Returns:
        Formatted list of recent news articles with titles, summaries, and sources
    """
    if not _live_news_service:
        return "Live news service is currently unavailable."
    
    try:
        # Ensure limit is reasonable
        limit = min(limit, 50)
        
        result = _live_news_service.get_live_news(limit=limit, source=source)
        
        if not result.get('success'):
            return f"Error getting news: {result.get('error', 'Unknown error')}"
        
        articles = result.get('data', [])
        
        if not articles:
            return "No news articles found."
        
        output = [f"Latest {len(articles)} news articles:\n"]
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            summary = article.get('summary', 'No summary')[:150]
            source = article.get('source', 'Unknown')
            sentiment = article.get('sentiment', 'Neutral')
            published = article.get('published', 'Unknown date')
            
            output.append(f"{i}. **{title}**")
            output.append(f"   Source: {source} | Sentiment: {sentiment}")
            output.append(f"   Published: {published}")
            output.append(f"   {summary}...\n")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting live news: {e}")
        return f"Error retrieving news: {str(e)}"

@tool
def get_news_by_sentiment(sentiment: str = "Positive", limit: int = 10) -> str:
    """Get news articles filtered by sentiment (Positive, Negative, or Neutral).
    
    Args:
        sentiment: "Positive", "Negative", or "Neutral" (default: Positive)
        limit: Maximum number of articles to return (default: 10, max: 20)
    
    Returns:
        Formatted list of news articles matching the sentiment filter
    """
    if not _live_news_service:
        return "Live news service is currently unavailable."
    
    # Validate sentiment
    valid_sentiments = ["Positive", "Negative", "Neutral"]
    if sentiment not in valid_sentiments:
        return f"Invalid sentiment. Choose from: {', '.join(valid_sentiments)}"
    
    try:
        # Ensure limit is reasonable
        limit = min(limit, 20)
        
        result = _live_news_service.get_news_by_sentiment(sentiment=sentiment, limit=limit)
        
        if not result.get('success'):
            return f"Error filtering news: {result.get('error', 'Unknown error')}"
        
        articles = result.get('data', [])
        
        if not articles:
            return f"No {sentiment.lower()} news articles found."
        
        output = [f"{sentiment} News ({len(articles)} articles):\n"]
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title')
            summary = article.get('summary', 'No summary')[:150]
            source = article.get('source', 'Unknown')
            published = article.get('published', 'Unknown date')
            
            output.append(f"{i}. **{title}**")
            output.append(f"   Source: {source}")
            output.append(f"   Published: {published}")
            output.append(f"   {summary}...\n")
        
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error filtering news by sentiment: {e}")
        return f"Error retrieving news: {str(e)}"

# List of all tools
tools = [
    # Navigation & UI
    change_theme, 
    go_to_detail_page, 
    go_to_projects,
    # Watchlist
    get_watchlist,
    add_to_watchlist, 
    remove_from_watchlist,
    # Company Info
    list_available_companies,
    get_detailed_company_info,
    # Project Info
    get_project_details,
    # RAG Search
    search_carbon_news,
    search_carbon_projects,
    # Live News Feed
    get_live_news,
    get_news_by_sentiment,
    # Web Search
    search_web
]

# ============================================================================
# INITIALIZE AGENT
# ============================================================================

agent = None

# System prompt for the agent
SYSTEM_PROMPT = """You are EcoInvest AI, a comprehensive assistant guiding users through EcoInvest - a Carbon Intelligence & ESG Investment Platform.

🌱 YOUR ROLE:
You're an expert guide helping users navigate sustainability investments, ESG analysis, carbon markets, and green projects. You have access to powerful tools for deep research and analysis.

🛠️ YOUR COMPREHENSIVE CAPABILITIES:

**Company Analysis:**
- get_detailed_company_info - Get stock price, ESG rating, GII score, industry, description
- list_available_companies - See all companies in database
- **For AI insights & future impact analysis**: Navigate to the company's report page using go_to_detail_page

**Carbon Projects:**
- get_project_details - Get basic project info (country, methodology, credits, price)
- search_carbon_projects - Search and discover carbon offset projects
- **For AI-generated project reports**: Navigate to the project's detail page using go_to_detail_page with project ID

**RAG-Powered Search (Real Data):**
- search_carbon_news - Search latest ESG/carbon/sustainability news articles with sources and custom query always use this first if no information is found then only use web search tool
- search_carbon_projects - Search carbon offset projects (renewable energy, REDD+, etc.)

**Live News Feed:**
- get_live_news - Get the latest news articles from the dashboard feed (limit: 1-50, optional source filter)
- get_news_by_sentiment - Filter news by sentiment (Positive/Negative/Neutral)

**Web Search:**
- search_web - Search the internet for current information, trends, and real-time data only when needed

**Platform Navigation:**
- go_to_detail_page - Navigate to company OR project detail pages (auto-detects type, or specify 'company'/'project')
- go_to_projects - Go to carbon projects marketplace (list view)
- change_theme - Toggle light/dark mode

**Watchlist:**
- get_watchlist - View all companies currently in the user's watchlist
- add_to_watchlist / remove_from_watchlist - Manage user's company watchlist

💡 HOW TO ASSIST:
- **Be proactive** - Guide users through the platform and suggest relevant tools
- **Use tools intelligently** - For basic company info, use get_detailed_company_info. For deeper insights/reports, navigate to their report page
- **News intelligence** - Use get_live_news for latest headlines, get_news_by_sentiment for sentiment-filtered news, and search_carbon_news for RAG-powered deep search
- **Search first** - When asked about news/trends/projects, USE the appropriate news tool (get_live_news for latest, search_carbon_news for specific topics). Use search_carbon_projects for carbon projects. For current events or general topics, use search_web
- **Navigate for reports** - When users ask for company insights, future impact, or comprehensive reports, navigate to the company's report page using go_to_detail_page
- **Navigate for project details** - When users ask about specific project details or reports, navigate to the project's detail page using go_to_detail_page with the project ID
- **Web search when needed** - Use search_web for current events, latest trends, or information not in the database
- **Be conversational** - Friendly, helpful tone. Explain ESG/carbon concepts simply
- **Provide context** - Don't just dump tool output - interpret and summarize key points
- **Offer next steps** - Suggest relevant actions ("Want me to add them to your watchlist?" or "Should I open their detailed report page?")

🎯 RESPONSE GUIDELINES:
- Keep responses clear and concise (2-4 paragraphs for complex topics)
- Use tools to get real data - don't make things up
- When using RAG tools, summarize the key findings naturally
- Explain technical terms (ESG, GII, carbon credits, REDD+) when needed
- Minimal emojis (1-2 max per response)
- When user asks to see/view a company report, navigate to the company page using go_to_detail_page
- When user asks to see/view a project report, navigate using go_to_detail_page with the project ID/code (e.g., "VCS-2126", "GS-1234")
- **IMPORTANT**: Carbon projects use IDs in format like "VCS-2126", "GS-1234" - use these EXACT codes when navigating to project pages

🚫 AVOID:
- Raw JSON or unformatted tool outputs
- Overly technical jargon without explanation
- Making up data when tools don't return results
- Being robotic or formal

You're the comprehensive guide to sustainable investing - help users discover, analyze, and understand green investments!"""

try:
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain/LangGraph not installed")

    # Get shared LLM instance from centralized manager
    model = get_llm()

    if not model:
        logger.error("❌ LLM not available - agent cannot be created")
        raise Exception("LLM initialization failed")

    # Message limit trimming can be applied to state using a state_modifier, but for simplicity
    # we just use the system prompt as the state_modifier

    # Create agent using modern langgraph API with memory support
    # MemorySaver provides conversation persistence across requests
    # This provides a production-ready agent implementation with ReAct loop
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=MemorySaver()
    )

    logger.info("✅ AI Chat agent initialized with 10-message limit and comprehensive tools (Gemini 2.5 Flash)")
except Exception as e:
    logger.error(f"❌ Failed to initialize AI chat agent: {e}")
    import traceback
    traceback.print_exc()
    agent = None

# ============================================================================
# API ENDPOINT
# ============================================================================

@aibot_bp.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint using LangChain agent with Gemini and tool calling."""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'default')
        
        logger.info(f"💬 Received message: {user_message}")
        
        # Check if agent is available
        if agent is None:
            logger.warning("⚠️ AI agent not initialized")
            return jsonify({
                'success': False,
                'error': 'AI service not available. Check Gemini API configuration.',
                'response': "Sorry, the AI service is currently unavailable. Please check the Gemini API configuration."
            }), 503
        
        # Invoke the agent using the modern API with memory support
        # The checkpointer automatically handles conversation history per thread_id
        # The agent follows the ReAct pattern and uses tools as needed
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            {"configurable": {"thread_id": session_id}}
        )
        
        # Extract the final response from the agent's message sequence
        # The last message in the result should be the agent's final response
        final_messages = result.get("messages", [])
        if final_messages:
            # Get the last message content - extract only the text, not metadata
            last_message = final_messages[-1]
            if hasattr(last_message, 'content'):
                # Handle AIMessage with content attribute
                content = last_message.content
                # If content is a list (multimodal), extract text parts
                if isinstance(content, list):
                    text_parts = [item.get('text', '') if isinstance(item, dict) else str(item) 
                                  for item in content if isinstance(item, dict) and item.get('type') == 'text']
                    bot_response = ' '.join(text_parts).strip()
                else:
                    bot_response = str(content).strip()
            elif isinstance(last_message, dict):
                bot_response = last_message.get('content', "I've processed your request.")
            else:
                bot_response = str(last_message)
        else:
            bot_response = "I've processed your request."
        
        # Convert markdown to HTML for proper formatting on frontend
        bot_response_html = markdown.markdown(bot_response, extensions=['nl2br', 'sane_lists'])
        
        # Keep chat history for client-side display (memory is handled by checkpointer)
        if session_id not in chat_histories:
            chat_histories[session_id] = []
        
        chat_histories[session_id].append({"role": "user", "content": user_message})
        chat_histories[session_id].append({"role": "assistant", "content": bot_response_html})
        
        # Keep last 20 messages (10 exchanges) for display purposes
        if len(chat_histories[session_id]) > 20:
            chat_histories[session_id] = chat_histories[session_id][-20:]
        
        # Log response (truncate if too long to avoid console spam)
        log_response = bot_response[:200] + "..." if len(bot_response) > 200 else bot_response
        logger.info(f"🤖 Responding: {log_response}")
        
        return jsonify({
            'success': True,
            'response': bot_response_html
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        quota_hit = "quota" in error_msg.lower()
        friendly = "Gemini quota exceeded. Please add billing or try again in a minute." if quota_hit else "Sorry, I encountered an error. Please try again."
        status_code = 429 if quota_hit else 500
        return jsonify({
            'success': False,
            'error': friendly,
            'response': friendly
        }), status_code
