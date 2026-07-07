"""
Flask Backend Application - Pathway Streaming

Main Flask application with REST API and WebSocket support.
Uses Pathway JSONL outputs for real-time data streaming.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import threading
import time
import logging

from pathway_reader import PathwayDataReader
from services.live_news_service import LiveNewsService
from services.watchlist_service import WatchlistService
from services.projects_service import ProjectsService
from services.analytics_service import AnalyticsService
from services.company_service import CompanyService
from services.project_report_service import ProjectReportService
from aibot import aibot_bp, set_pathway_reader, set_company_service, set_project_service, set_projects_service, set_live_news_service
import frontend_actions

# Import RAG services for vector store initialization
try:
    from services.news_rag_service import get_news_rag_service
    from services.projects_rag_service import get_projects_rag_service
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"⚠️ RAG services not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# CORS configuration
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',') if ',' in os.getenv('CORS_ORIGINS', '*') else '*'
CORS(app, resources={r"/*": {"origins": cors_origins}})

# Register blueprints
app.register_blueprint(aibot_bp)

# Initialize SocketIO with error suppression
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    logger=False,  # Suppress socketio logs
    engineio_logger=False,  # Suppress engine.io logs
    ping_timeout=60,  # Increase timeout for slower connections
    ping_interval=25,  # Send ping every 25 seconds
    max_http_buffer_size=1e8  # Handle larger payloads
)

# Set socketio for frontend actions (enables AI chatbot to control frontend)
frontend_actions.set_socketio(socketio)

# Initialize pathway reader
logger.info("🚀 Initializing Pathway Data Reader...")
pathway_output_dir = os.getenv('PATHWAY_OUTPUT_DIR', './carbon-intelligence/server/output')
pathway_reader = PathwayDataReader(pathway_output_dir=pathway_output_dir)

# Initialize modular services - each service corresponds to a frontend feature
logger.info("📦 Initializing Modular Services...")
live_news_service = LiveNewsService(pathway_reader)
watchlist_service = WatchlistService(pathway_reader)
projects_service = ProjectsService(pathway_reader)
analytics_service = AnalyticsService(pathway_reader)
company_service = CompanyService(pathway_reader)
project_report_service = ProjectReportService(pathway_reader)

# Connect pathway_reader to aibot for company name resolution
set_pathway_reader(pathway_reader)

# Connect services to aibot for comprehensive tool access
set_company_service(company_service)
set_project_service(project_report_service)
set_projects_service(projects_service)
set_live_news_service(live_news_service)

# Initialize RAG services in background so server starts immediately
def _init_rag_services():
    """Background thread to initialize RAG vector stores."""
    logger.info("📚 Initializing RAG services in background...")
    print("\n" + "="*70)
    print("📚 INITIALIZING RAG VECTOR STORES (background)")
    print("="*70)
    
    # Initialize News RAG
    logger.info("📰 Initializing News RAG Service...")
    news_rag = get_news_rag_service()
    if news_rag:
        logger.info("✅ News RAG Service initialized")
    else:
        logger.warning("⚠️ News RAG Service failed to initialize")
    
    # Initialize Projects RAG
    logger.info("🌍 Initializing Projects RAG Service...")
    projects_rag = get_projects_rag_service()
    if projects_rag:
        logger.info("✅ Projects RAG Service initialized")
    else:
        logger.warning("⚠️ Projects RAG Service failed to initialize")
    
    print("="*70)
    print("✅ RAG SERVICES READY")
    print("="*70 + "\n")

if RAG_AVAILABLE:
    import threading
    rag_thread = threading.Thread(target=_init_rag_services, daemon=True)
    rag_thread.start()
else:
    logger.warning("⚠️ RAG Services not available - install langchain-community, faiss-cpu, sentence-transformers")

logger.info("✅ All services initialized!")

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f'📡 Client connected: {request.sid}')
    emit('connection_response', {
        'status': 'connected',
        'message': 'Connected to Carbon Intelligence Backend'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f'📡 Client disconnected: {request.sid}')

@socketio.on('request_data')
def handle_data_request(data):
    """Handle data requests from frontend - using modular services"""
    data_type = data.get('type', 'analytics')
    try:
        if data_type == 'projects':
            result = projects_service.get_all_projects(limit=100)
            emit('projects_update', result)
        elif data_type == 'finance':
            companies = watchlist_service.get_all_companies()
            emit('finance_update', {'success': True, 'data': companies})
        elif data_type == 'news':
            result = live_news_service.get_live_news(limit=50)
            emit('news_update', result)
        elif data_type == 'analytics':
            result = analytics_service.get_dashboard_analytics()
            emit('analytics_update', result)
    except Exception as e:
        logger.error(f"Error handling data request: {e}")
        emit('error', {'error': str(e)})

@socketio.on('watchlist_update')
def handle_watchlist_update(data):
    """Receive watchlist updates from frontend"""
    try:
        watchlist = data.get('watchlist', [])
        frontend_actions.update_watchlist_state(watchlist)
        logger.info(f"📋 Received watchlist update: {len(watchlist)} companies")
    except Exception as e:
        logger.error(f"Error handling watchlist update: {e}")

# Background data pusher - broadcasts on data changes
def background_data_pusher():
    """Monitor for data changes and broadcast immediately"""
    last_broadcast = None
    min_broadcast_interval = 1  # Minimum 1 second between broadcasts to avoid thrashing
    
    while True:
        try:
            time.sleep(0.5)  # Check frequently for changes
            
            # Check if data has changed
            if pathway_reader.has_changes():
                now = time.time()
                # Enforce minimum interval between broadcasts
                if last_broadcast is None or (now - last_broadcast) >= min_broadcast_interval:
                    analytics = analytics_service.get_dashboard_analytics()
                    # Broadcast to all clients - send the full analytics object
                    socketio.emit('data_update', {
                        'analytics': analytics,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info("🔴 LIVE UPDATE: Broadcasting data changes to all clients")
                    last_broadcast = now
        except Exception as e:
            logger.error(f"Error in background pusher: {e}")
            time.sleep(1)

pusher_thread = threading.Thread(target=background_data_pusher, daemon=True)
pusher_thread.start()

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'live_news': 'operational',
            'watchlist': 'operational',
            'projects': 'operational',
            'analytics': 'operational',
            'company': 'operational'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/search/fast', methods=['GET'])
def fast_rag_search():
    """Use Hybrid Search (BM25 + FAISS) to search both news and projects"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400
        
    try:
        # Import dynamically to avoid circular dependencies
        from services.news_rag_service import search_news
        from services.projects_rag_service import search_projects
        
        # Parallel fetch could be added here, but sequential is fine for now 
        # since individual latencies are sub-second
        news_results = search_news(query, limit=3)
        project_results = search_projects(query, limit=3)
        
        return jsonify({
            'success': True,
            'data': {
                'news': news_results,
                'projects': project_results
            }
        })
    except Exception as e:
        logger.error(f"Error in fast search: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# ANALYTICS ENDPOINTS (Dashboard Overview)
# ============================================================================

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics dashboard - calls AnalyticsService"""
    return jsonify(analytics_service.get_dashboard_analytics())

@app.route('/api/analytics/esg', methods=['POST'])
def analyze_esg():
    """Analyze ESG scores - calls AnalyticsService"""
    data = request.json or {}
    tickers = data.get('tickers', None)
    result = analytics_service.get_esg_analysis(tickers=tickers)
    return jsonify(result)

@app.route('/api/analytics/carbon-trends', methods=['GET'])
def analyze_carbon_trends():
    """Analyze carbon trends - calls AnalyticsService"""
    result = analytics_service.get_carbon_trends()
    return jsonify(result)

@app.route('/api/analytics/news-sentiment', methods=['GET'])
def analyze_news_sentiment():
    """Analyze news sentiment - calls AnalyticsService"""
    result = analytics_service.get_news_sentiment_analysis()
    return jsonify(result)

@app.route('/api/analytics/market-summary', methods=['GET'])
def get_market_summary():
    """Get market summary - calls AnalyticsService"""
    result = analytics_service.get_market_summary()
    return jsonify(result)

# ============================================================================
# PROJECTS ENDPOINTS (Carbon Marketplace)
# ============================================================================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all projects - calls ProjectsService"""
    limit = request.args.get('limit', 1000, type=int)
    country = request.args.get('country', None)
    category = request.args.get('category', None)
    result = projects_service.get_all_projects(limit=limit, country=country, category=category)
    return jsonify(result)

@app.route('/api/project/<project_id>', methods=['GET'])
def get_project_details(project_id):
    """Section 1: Get project details - calls ProjectReportService"""
    result = project_report_service.get_project_details(project_id)
    return jsonify(result)

@app.route('/api/project/<project_id>/report', methods=['GET'])
def get_project_report(project_id):
    """Section 2: Generate project report - calls ProjectReportService"""
    force_refresh = request.args.get('forceRefresh', 'false').lower() == 'true'
    only_cached = request.args.get('onlyCached', 'false').lower() == 'true'
    result = project_report_service.generate_project_report(project_id, force_refresh, only_cached)
    return jsonify(result)

@app.route('/api/project/<project_id>/custom-query', methods=['POST'])
def project_custom_query(project_id):
    """Section 3: Answer questions about project - calls ProjectReportService"""
    data = request.json or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'success': False, 'error': 'Query is required'}), 400
    result = project_report_service.custom_query(project_id, query)
    return jsonify(result)

@app.route('/api/projects/search', methods=['POST'])
def search_projects():
    """Search projects - calls ProjectsService"""
    data = request.json
    query = data.get('query', '')
    limit = data.get('limit', 100)
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400
    result = projects_service.search_projects(query, limit=limit)
    return jsonify(result)

# ============================================================================
# WATCHLIST/COMPANY ENDPOINTS (Dashboard Watchlist)
# ============================================================================

@app.route('/api/finance', methods=['GET'])
def get_finance():
    """Get finance data - calls WatchlistService"""
    ticker = request.args.get('ticker', None)
    if ticker:
        result = watchlist_service.get_company_by_ticker(ticker)
        return jsonify(result)
    else:
        companies = watchlist_service.get_all_companies()
        return jsonify({'success': True, 'count': len(companies), 'data': companies})

@app.route('/api/finance/<ticker>', methods=['GET'])
def get_finance_by_ticker(ticker):
    """Get finance by ticker - calls WatchlistService"""
    result = watchlist_service.get_company_by_ticker(ticker)
    return jsonify(result)

@app.route('/api/watchlist/search', methods=['POST'])
def search_watchlist():
    """Search companies for watchlist - calls WatchlistService"""
    data = request.json
    query = data.get('query', '')
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400
    results = watchlist_service.search_companies(query)
    return jsonify({'success': True, 'count': len(results), 'data': results})

@app.route('/api/watchlist/summary', methods=['POST'])
def get_watchlist_summary():
    """Get watchlist summary - calls WatchlistService"""
    data = request.json
    ticker_list = data.get('tickers', [])
    result = watchlist_service.get_watchlist_summary(ticker_list)
    return jsonify(result)

# ============================================================================
# NEWS ENDPOINTS (Dashboard News Feed)
# ============================================================================

@app.route('/api/news', methods=['GET'])
def get_news():
    """Get news articles - calls LiveNewsService"""
    limit = request.args.get('limit', 200, type=int)
    source = request.args.get('source', None)
    result = live_news_service.get_live_news(limit=limit, source=source)
    return jsonify(result)

@app.route('/api/news/sentiment/<sentiment>', methods=['GET'])
def get_news_by_sentiment(sentiment):
    """Get news by sentiment - calls LiveNewsService"""
    limit = request.args.get('limit', 20, type=int)
    result = live_news_service.get_news_by_sentiment(sentiment=sentiment, limit=limit)
    return jsonify(result)

# ============================================================================
# COMPANY DETAIL ENDPOINTS (Report Page)
# ============================================================================

@app.route('/api/company/<ticker>', methods=['GET'])
def get_company_details(ticker):
    """Get company details - calls CompanyService"""
    result = company_service.get_company_details(ticker)
    return jsonify(result)

@app.route('/api/company/<ticker>/insights', methods=['GET'])
def get_company_insights(ticker):
    """Get general company insights - calls CompanyService"""
    force_refresh = request.args.get('forceRefresh', 'false').lower() == 'true'
    only_cached = request.args.get('onlyCached', 'false').lower() == 'true'
    result = company_service.get_company_insights(ticker, force_refresh, only_cached)
    return jsonify(result)

@app.route('/api/company/<ticker>/future-impact', methods=['GET'])
def get_future_impact_analysis(ticker):
    """Get sustainability and future impact analysis - calls CompanyService"""
    force_refresh = request.args.get('forceRefresh', 'false').lower() == 'true'
    only_cached = request.args.get('onlyCached', 'false').lower() == 'true'
    result = company_service.get_future_impact_analysis(ticker, force_refresh, only_cached)
    return jsonify(result)

@app.route('/api/company/<ticker>/custom-query', methods=['POST'])
def custom_query(ticker):
    """Answer custom questions about the company - calls CompanyService"""
    data = request.json or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'success': False, 'error': 'Query is required'}), 400
    result = company_service.custom_query(ticker, query)
    return jsonify(result)

# ============================================================================
# FRONTEND ACTION ENDPOINTS (for testing and direct API calls)
# ============================================================================

@app.route('/api/frontend/change_theme', methods=['POST'])
def api_change_theme():
    """Change frontend theme via API"""
    success = frontend_actions.change_theme()
    return jsonify({'success': success, 'message': 'Theme changed' if success else 'Failed to change theme'})

@app.route('/api/frontend/add_to_watchlist', methods=['POST'])
def api_add_to_watchlist():
    """Add company to watchlist via API"""
    data = request.get_json() or {}
    company_name = data.get('company_name', 'Unknown')
    ticker = data.get('ticker', company_name)
    success = frontend_actions.add_company_to_watchlist(company_name, ticker)
    return jsonify({'success': success, 'message': f'Added {company_name} to watchlist' if success else 'Failed'})

@app.route('/api/frontend/remove_from_watchlist', methods=['POST'])
def api_remove_from_watchlist():
    """Remove company from watchlist via API"""
    data = request.get_json() or {}
    company_name = data.get('company_name', 'Unknown')
    success = frontend_actions.remove_company_from_watchlist(company_name)
    return jsonify({'success': success, 'message': f'Removed {company_name} from watchlist' if success else 'Failed'})

@app.route('/api/frontend/navigate', methods=['POST'])
def api_navigate():
    """Navigate to a page via API"""
    data = request.get_json() or {}
    page = data.get('page', 'company')
    company_name = data.get('company_name')
    ticker = data.get('ticker')
    
    if page == 'projects':
        success = frontend_actions.go_to_projects_page()
    else:
        success = frontend_actions.go_to_company_page(company_name or 'Unknown', ticker)
    
    return jsonify({'success': success, 'message': f'Navigating to {page}' if success else 'Failed'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Starting Carbon Intelligence Backend on port {port}")
    logger.info(f"📊 Debug mode: {debug}")
    logger.info(f"🌐 WebSocket support: Enabled")
    logger.info(f"📡 Real-time updates: On data changes")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=debug, 
        use_reloader=False,
        allow_unsafe_werkzeug=True,
        log_output=debug  # Only show werkzeug logs in debug mode
    )
