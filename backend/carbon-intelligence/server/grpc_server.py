from concurrent import futures
import threading
import time
import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

import carbon_service_pb2 as pb2
import carbon_service_pb2_grpc as pb2_grpc
import grpc
import pathway as pw
from pipeline import build_pipeline
from redis_cache import cache_get, cache_set

unified, finance, news = build_pipeline()

OUTPUT_DIR = "./output"
PROJECTS_FILE = os.path.join(OUTPUT_DIR, "projects.jsonl")
NEWS_FILE = os.path.join(OUTPUT_DIR, "news.jsonl")

# PostgreSQL connection settings
DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "carbon_intel",
    "user": "carbon",
    "password": "carbonpw"
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)

def read_jsonl_file(filepath):
    """Read JSONL file and return list of records"""
    if not os.path.exists(filepath):
        return []
    
    records = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line.strip())
                    if isinstance(data, list) and len(data) > 0:
                        records.append(data[0])
                    elif isinstance(data, dict):
                        records.append(data)
    except Exception as e:
        print(f"⚠️  Error reading {filepath}: {e}")
    
    return records


class CarbonServicer(pb2_grpc.CarbonServiceServicer):
    def GetProjects(self, request, context):
        key = f"projects:{request.country or 'ALL'}"
        cached = cache_get(key)

        if cached:
            return pb2.ProjectResponse(items=[pb2.ProjectItem(**x) for x in cached])

        try:
            projects = read_jsonl_file(PROJECTS_FILE)
            
            if request.country:
                projects = [p for p in projects if p.get('country') == request.country]
            
            results = [
                {
                    "project_id": p.get("project_id", ""),
                    "project_name": p.get("project_name", ""),
                    "description": p.get("description", ""),
                    "methodology": p.get("methodology", "Verra VCS"),
                    "registry_status": p.get("registry_status", ""),
                    "country": p.get("country", ""),
                    "vintage": int(p.get("vintage", 0)),
                    "supply": float(p.get("available_credits", 0)),
                    "price": float(p.get("price", 0.0)),
                    "available_credits": int(p.get("available_credits", 0)),
                    "category": p.get("category", ""),
                    "image_url": p.get("image_url", ""),
                    "buy_link": p.get("buy_link", ""),
                    "project_summary": p.get("project_summary", ""),
                }
                for p in projects
            ]
            
        except Exception as e:
            print(f"❌ Error reading projects from Pathway output: {e}")
            results = []

        cache_set(key, results)
        return pb2.ProjectResponse(items=[pb2.ProjectItem(**x) for x in results])

    def GetNews(self, request, context):
        key = f"news:{request.source or 'ALL'}"
        cached = cache_get(key)

        if cached:
            return pb2.NewsResponse(items=[pb2.NewsItem(**x) for x in cached])

        try:
            news_items = read_jsonl_file(NEWS_FILE)
            
            if request.source:
                news_items = [n for n in news_items if n.get('source') == request.source]
            
            news_items = news_items[:100]
            
            results = [
                {
                    "id": n.get("news_id", n.get("id", n.get("guid", ""))),
                    "guid": n.get("guid", ""),
                    "title": n.get("title", ""),
                    "summary": n.get("summary", ""),
                    "body": n.get("body", n.get("summary", "")),
                    "author": n.get("author", "Staff Writer"),
                    "date": n.get("date", n.get("published", "")),
                    "link": n.get("link", ""),
                    "published": n.get("published", ""),
                    "source": n.get("source", ""),
                    "sentiment": n.get("sentiment", "Neutral"),
                    "image_url": n.get("image_url", ""),
                }
                for n in news_items
            ]
            
        except Exception as e:
            print(f"❌ Error reading news from Pathway output: {e}")
            results = []

        cache_set(key, results)
        return pb2.NewsResponse(items=[pb2.NewsItem(**x) for x in results])

    def GetFinanceData(self, request, context):
        """Get real-time finance/stock data with full company metadata"""
        cache_key = f"finance:{request.ticker if request.ticker else 'ALL'}"
        
        # Check cache
        cached = cache_get(cache_key)
        if cached:
            return pb2.FinanceResponse(
                items=[pb2.FinanceItem(**item) for item in cached['items']],
                count=cached['count']
            )
        
        try:
            finance_file = os.path.join(OUTPUT_DIR, "finance.jsonl")
            with open(finance_file, 'r') as f:
                lines = f.readlines()
            
            items = []
            for line in lines[-1000:]:  # Last 1000 records
                try:
                    data = json.loads(line)
                    if data.get('diff', 1) == 1:  # Only active records
                        if not request.ticker or data.get('ticker') == request.ticker:
                            item_dict = {
                                'ticker': data.get('ticker', ''),
                                'company_name': data.get('company_name', data.get('ticker', '')),
                                'industry': data.get('industry', 'Technology'),
                                'description': data.get('description', ''),
                                'gii_score': int(data.get('gii_score', 75)),
                                'stock_price': float(data.get('stock_price', data.get('price', 0))),
                                'market_cap': str(data.get('market_cap', '0B')),
                                'sustainability_update': data.get('sustainability_update', ''),
                                'esg_rating': data.get('esg_rating', 'A'),
                                'website': data.get('website', ''),
                                'price': float(data.get('price', 0)),
                                'volume': int(data.get('volume', 0)),
                                'change_percent': float(data.get('change_percent', 0)),
                                'timestamp': int(data.get('timestamp', 0))
                            }
                            items.append(item_dict)
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    continue
            
            response = {
                'items': items,
                'count': len(items)
            }
            
            cache_set(cache_key, response, ttl=60)  # Cache for 1 minute
            return pb2.FinanceResponse(
                items=[pb2.FinanceItem(**item) for item in items],
                count=len(items)
            )
            
        except FileNotFoundError:
            return pb2.FinanceResponse(items=[], count=0)
    
    def GetProjectDetail(self, request, context):
        """Get detailed project information by project_id"""
        cache_key = f"project_detail:{request.project_id}"
        
        # Check cache
        cached = cache_get(cache_key)
        if cached:
            return pb2.ProjectDetailResponse(**cached)
        
        try:
            # Search in projects.jsonl via OUTPUT_DIR constant
            projects_file = os.path.join(OUTPUT_DIR, "projects.jsonl")
            with open(projects_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get('project_id') == request.project_id and data.get('diff', 1) == 1:
                            project = pb2.ProjectDetail(
                                project_id=data.get('project_id', ''),
                                project_name=data.get('project_name', ''),
                                registry_status=data.get('registry_status', ''),
                                country=data.get('country', ''),
                                vintage=int(data.get('vintage', 0)),
                                supply=float(data.get('supply', 0)),
                                project_summary=data.get('project_summary', ''),
                                project_link=data.get('project_link', ''),
                                source='verra'
                            )
                            
                            response = {'project': {
                                'project_id': project.project_id,
                                'project_name': project.project_name,
                                'registry_status': project.registry_status,
                                'country': project.country,
                                'vintage': project.vintage,
                                'supply': project.supply,
                                'project_summary': project.project_summary,
                                'project_link': project.project_link,
                                'source': project.source
                            }}
                            
                            cache_set(cache_key, response)
                            return pb2.ProjectDetailResponse(**response)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
            
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f'Project {request.project_id} not found')
            return pb2.ProjectDetailResponse()
            
        except FileNotFoundError:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Projects data not available')
            return pb2.ProjectDetailResponse()
    
    # ============================================================
    # NON-STREAMING ENDPOINTS - Direct SQL Queries
    # ============================================================
    
    def GetNonStreamingProjects(self, request, context):
        """Get projects directly from PostgreSQL database (non-streaming)"""
        cache_key = f"nonstreaming_projects:{request.country or 'ALL'}"
        
        # Check cache
        cached = cache_get(cache_key)
        if cached:
            return pb2.ProjectResponse(items=[pb2.ProjectItem(**x) for x in cached])
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query based on filter - now includes all new fields
            if request.country:
                query = """
                    SELECT DISTINCT ON (v.project_id)
                        v.project_id,
                        COALESCE(c.project_name, v.project_name) as project_name,
                        v.description,
                        v.methodology,
                        v.registry_status,
                        v.country,
                        v.vintage,
                        v.price,
                        v.available_credits,
                        v.category,
                        v.image_url,
                        v.buy_link,
                        v.project_summary
                    FROM verra v
                    LEFT JOIN carbonmark c ON v.project_id = c.project_id
                    WHERE v.country = %s
                    ORDER BY v.project_id, v.updated_at DESC
                """
                cursor.execute(query, (request.country,))
            else:
                query = """
                    SELECT DISTINCT ON (v.project_id)
                        v.project_id,
                        COALESCE(c.project_name, v.project_name) as project_name,
                        v.description,
                        v.methodology,
                        v.registry_status,
                        v.country,
                        v.vintage,
                        v.price,
                        v.available_credits,
                        v.category,
                        v.image_url,
                        v.buy_link,
                        v.project_summary
                    FROM verra v
                    LEFT JOIN carbonmark c ON v.project_id = c.project_id
                    ORDER BY v.project_id, v.updated_at DESC
                """
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            results = [
                {
                    "project_id": row['project_id'] or '',
                    "project_name": row['project_name'] or '',
                    "description": row.get('description', ''),
                    "methodology": row.get('methodology', 'Verra VCS'),
                    "registry_status": row.get('registry_status', ''),
                    "country": row.get('country', ''),
                    "vintage": int(row.get('vintage', 0) or 0),
                    "supply": float(row.get('available_credits', 0) or 0),
                    "price": float(row.get('price', 0) or 0),
                    "available_credits": int(row.get('available_credits', 0) or 0),
                    "category": row.get('category', ''),
                    "image_url": row.get('image_url', ''),
                    "buy_link": row.get('buy_link', ''),
                    "project_summary": row.get('project_summary', ''),
                }
                for row in rows
            ]
            
            cursor.close()
            conn.close()
            
            # Cache for 5 minutes
            cache_set(cache_key, results)
            
            return pb2.ProjectResponse(items=[pb2.ProjectItem(**x) for x in results])
            
        except Exception as e:
            print(f"❌ Error reading projects from database: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Database error: {str(e)}')
            return pb2.ProjectResponse(items=[])
    
    def GetNonStreamingNews(self, request, context):
        """Get news directly from PostgreSQL database (non-streaming)"""
        cache_key = f"nonstreaming_news:{request.source or 'ALL'}"
        
        # Check cache
        cached = cache_get(cache_key)
        if cached:
            return pb2.NewsResponse(items=[pb2.NewsItem(**x) for x in cached])
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query based on filter - now includes all new fields
            if request.source:
                query = """
                    SELECT id, guid, title, summary, body, author, date, 
                           link, published, source, sentiment, image_url
                    FROM news
                    WHERE source = %s
                    ORDER BY date DESC
                    LIMIT 100
                """
                cursor.execute(query, (request.source,))
            else:
                query = """
                    SELECT id, guid, title, summary, body, author, date,
                           link, published, source, sentiment, image_url
                    FROM news
                    ORDER BY date DESC
                    LIMIT 100
                """
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            results = [
                {
                    "id": row.get("id", row.get("guid", "")),
                    "guid": row.get("guid", ""),
                    "title": row.get("title", ""),
                    "summary": row.get("summary", ""),
                    "body": row.get("body", row.get("summary", "")),
                    "author": row.get("author", "Staff Writer"),
                    "date": row.get("date", row.get("published", "")),
                    "link": row.get("link", ""),
                    "published": row.get("published", ""),
                    "source": row.get("source", ""),
                    "sentiment": row.get("sentiment", "Neutral"),
                    "image_url": row.get("image_url", ""),
                }
                for row in rows
            ]
            
            cursor.close()
            conn.close()
            
            # Cache for 5 minutes
            cache_set(cache_key, results)
            
            return pb2.NewsResponse(items=[pb2.NewsItem(**x) for x in results])
            
        except Exception as e:
            print(f"❌ Error reading news from database: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Database error: {str(e)}')
            return pb2.NewsResponse(items=[])
    
    def GetNonStreamingFinanceData(self, request, context):
        """Get finance data directly from PostgreSQL database (non-streaming)"""
        cache_key = f"nonstreaming_finance:{request.ticker or 'ALL'}"
        
        # Check cache
        cached = cache_get(cache_key)
        if cached:
            return pb2.FinanceResponse(**cached)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Build query based on filter - now includes all new fields
            if request.ticker:
                query = """
                    SELECT ticker, company_name, industry, description, gii_score,
                           stock_price, market_cap, sustainability_update, esg_rating,
                           website, price, volume, change_percent, timestamp
                    FROM finance
                    WHERE ticker = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                cursor.execute(query, (request.ticker,))
            else:
                query = """
                    SELECT DISTINCT ON (ticker)
                        ticker, company_name, industry, description, gii_score,
                        stock_price, market_cap, sustainability_update, esg_rating,
                        website, price, volume, change_percent, timestamp
                    FROM finance
                    ORDER BY ticker, timestamp DESC
                """
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            items = [
                pb2.FinanceItem(
                    ticker=row.get("ticker", ""),
                    company_name=row.get("company_name", row.get("ticker", "")),
                    industry=row.get("industry", "Technology"),
                    description=row.get("description", ""),
                    gii_score=int(row.get("gii_score", 75) or 75),
                    stock_price=float(row.get("stock_price", row.get("price", 0)) or 0),
                    market_cap=str(row.get("market_cap", "0B")),
                    sustainability_update=row.get("sustainability_update", ""),
                    esg_rating=row.get("esg_rating", "A"),
                    website=row.get("website", ""),
                    price=float(row.get("price", 0) or 0),
                    volume=int(row.get("volume", 0) or 0),
                    change_percent=float(row.get("change_percent", 0) or 0),
                    timestamp=int(row.get("timestamp", 0) or 0)
                )
                for row in rows
            ]
            
            cursor.close()
            conn.close()
            
            response = {
                'items': [
                    {
                        'ticker': item.ticker,
                        'company_name': item.company_name,
                        'industry': item.industry,
                        'description': item.description,
                        'gii_score': item.gii_score,
                        'stock_price': item.stock_price,
                        'market_cap': item.market_cap,
                        'sustainability_update': item.sustainability_update,
                        'esg_rating': item.esg_rating,
                        'website': item.website,
                        'price': item.price,
                        'volume': item.volume,
                        'change_percent': item.change_percent,
                        'timestamp': item.timestamp
                    } for item in items
                ],
                'count': len(items)
            }
            
            # Cache for 5 minutes
            cache_set(cache_key, response)
            
            return pb2.FinanceResponse(**response)
            
        except Exception as e:
            print(f"❌ Error reading finance data from database: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Database error: {str(e)}')
            return pb2.FinanceResponse(items=[], count=0)


def _run_pathway_supervised():
    """Run the Pathway pipeline in a loop, restarting on crash.
    Uses exponential backoff (5s → 10s → 20s → ... → 60s cap).
    This fixes BUG-01: Pathway was a daemon thread that died silently,
    leaving the gRPC server serving stale JSONL data with no auto-recovery.
    """
    backoff = 5
    while True:
        print(f"⚡ Starting Pathway pipeline thread (backoff={backoff}s)...")
        t = threading.Thread(target=pw.run, daemon=True)
        t.start()
        t.join()  # blocks until pathway thread exits (crash or clean stop)
        print(f"⚠️  Pathway thread exited. Restarting in {backoff}s...")
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)  # exponential backoff, cap at 60s


def serve():
    print("📡 Starting gRPC server on port 50051...")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    pb2_grpc.add_CarbonServiceServicer_to_server(CarbonServicer(), server)
    server.add_insecure_port("[::]:50051")

    print("⚙️  Starting Pathway runtime (supervised)...")
    pathway_supervisor = threading.Thread(
        target=_run_pathway_supervised,
        daemon=True,
        name="pathway-supervisor"
    )
    pathway_supervisor.start()

    # Give Pathway time to connect to Kafka and build first batch
    time.sleep(5)

    server.start()
    print("✅ gRPC server ready on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
