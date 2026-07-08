"""
Pathway Data Reader - Reads data from Pathway output files or directly from Postgres
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PathwayDataReader:
    """Reads and analyzes data from Pathway output files or Postgres database"""
    
    def __init__(self, pathway_output_dir: str = "./carbon-intelligence/server/output"):
        self.output_dir = pathway_output_dir
        self.projects_file = os.path.join(pathway_output_dir, "projects.jsonl")
        self.finance_file = os.path.join(pathway_output_dir, "finance.jsonl")
        self.news_file = os.path.join(pathway_output_dir, "news.jsonl")
        
        # Database connection for direct access
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'dbname': os.getenv('DB_NAME', 'carbon_intel'),
            'user': os.getenv('DB_USER', 'carbon'),
            'password': os.getenv('DB_PASSWORD', 'carbonpw')
        }
        self.use_db = self._test_db_connection()
        
        # gRPC tier: Flask → gRPC → carbon_pathway → Pathway data
        # Tested once at startup; if carbon_pathway isn't up yet, falls back to DB
        self.use_grpc = self._test_grpc_connection()
        
        # Cache with timestamps and file modification tracking
        self._cache = {
            'projects': {'data': [], 'timestamp': None, 'file_mtime': None},
            'finance': {'data': [], 'timestamp': None, 'file_mtime': None},
            'news': {'data': [], 'timestamp': None, 'file_mtime': None}
        }
        self._cache_ttl = 2  # Cache for 2 seconds minimum (to avoid thrashing)
        
        # DB-change polling state (for has_changes() when use_db=True)
        self._last_db_poll: float = 0.0
        self._last_news_ts: str   = None
        self._last_finance_ts: str = None
        self._last_verra_ts: str  = None
        
        self.socketio = None
        
        logger.info(f"✅ Pathway reader initialized: {pathway_output_dir}")
        if self.use_grpc:
            logger.info(f"⚡ gRPC tier enabled (carbon_pathway:{os.getenv('PATHWAY_GRPC_PORT','50051')})")
        elif self.use_db:
            logger.info(f"✅ Direct database connection enabled: {self.db_config['host']}")
        else:
            logger.info("📁 Falling back to JSONL file reads")
            
        self._setup_watchdog()
        
    def set_socketio(self, socketio):
        """Set the SocketIO instance to emit latency updates"""
        self.socketio = socketio
        
    def _setup_watchdog(self):
        """Setup OS-level file watcher using watchdog"""
        class PathwayEventHandler(FileSystemEventHandler):
            def __init__(self, reader):
                self.reader = reader
                
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.jsonl'):
                    self.reader._handle_file_change(event.src_path)
                    
        try:
            self.observer = Observer()
            handler = PathwayEventHandler(self)
            # Make sure directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            self.observer.schedule(handler, self.output_dir, recursive=False)
            self.observer.start()
            logger.info(f"👀 Watchdog monitoring {self.output_dir} for changes")
        except Exception as e:
            logger.error(f"Failed to start watchdog: {e}")
            
    def _handle_file_change(self, filepath: str):
        """Process a file change event and emit latency"""
        filename = os.path.basename(filepath)
        
        # Determine cache key
        cache_key = None
        if filename == 'finance.jsonl': cache_key = 'finance'
        elif filename == 'news.jsonl': cache_key = 'news'
        elif filename == 'projects.jsonl': cache_key = 'projects'
        
        if cache_key:
            # Refresh cache immediately
            self._cache[cache_key]['file_mtime'] = os.path.getmtime(filepath)
            
            # Read the latest record to compute latency
            records = self._read_jsonl_file(filepath, max_records=5)
            if records and self.socketio:
                latest = records[-1]
                # Look for a timestamp from the scraper
                scraper_ts = latest.get('timestamp') or latest.get('time')
                if scraper_ts:
                    # Convert to seconds if in ms
                    if scraper_ts > 10000000000: 
                        scraper_ts = scraper_ts / 1000.0
                        
                    latency_ms = (time.time() - scraper_ts) * 1000
                    
                    # Prevent negative latency from clock skew
                    if latency_ms >= 0:
                        self.socketio.emit('latency_update', {
                            'source': cache_key,
                            'latency_ms': round(latency_ms, 2)
                        })
    
    def _test_grpc_connection(self) -> bool:
        """Test if the carbon_pathway gRPC server is reachable."""
        try:
            from grpc_client import test_grpc_connection
            return test_grpc_connection()
        except Exception as e:
            logger.warning(f"gRPC client import error: {e}")
            return False

    def _test_db_connection(self) -> bool:
        """Test if database connection is available"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {e}, falling back to JSONL files")
            return False
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def _read_jsonl_file(self, filepath: str, max_records: int = None) -> List[Dict]:
        """Read JSONL file and return list of active records"""
        if not os.path.exists(filepath):
            return []
        
        records = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if max_records:
                    lines = lines[-max_records:]
                
                for line in lines:
                    if line.strip():
                        data = json.loads(line.strip())
                        if data.get('diff', 1) == 1:
                            records.append(data)
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
        
        return records
    
    def _file_changed(self, filepath: str, cache_key: str) -> bool:
        """Check if file has been modified"""
        if not os.path.exists(filepath):
            return False
        
        try:
            current_mtime = os.path.getmtime(filepath)
            cached_mtime = self._cache[cache_key]['file_mtime']
            
            if cached_mtime is None:
                self._cache[cache_key]['file_mtime'] = current_mtime
                return False  # First time checking, no change yet
            
            if current_mtime > cached_mtime:
                self._cache[cache_key]['file_mtime'] = current_mtime
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking file modification time: {e}")
            return False
    
    def _should_refresh_cache(self, cache_key: str, filepath: str) -> bool:
        """Check if cache should be refreshed based on file changes or TTL"""
        # Always check if file changed
        if self._file_changed(filepath, cache_key):
            return True
        
        # Fall back to TTL check
        if self._cache[cache_key]['timestamp'] is None:
            return True
        age = (datetime.now() - self._cache[cache_key]['timestamp']).total_seconds()
        return age > self._cache_ttl
    
    def get_projects(self, country: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """Get carbon projects — gRPC → DB → JSONL fallback chain."""
        # Tier 1: gRPC (data through Pathway pipeline)
        if self.use_grpc:
            try:
                from grpc_client import get_projects_grpc
                projects = get_projects_grpc(country=country, limit=limit)
                if projects:
                    logger.info(f"⚡ gRPC: {len(projects)} projects")
                    return projects
            except Exception as e:
                logger.warning(f"gRPC projects tier failed: {e}")

        # Tier 2: Direct DB
        if self.use_db:
            try:
                conn = self._get_db_connection()
                cur = conn.cursor()
                query  = "SELECT * FROM verra"
                params = []
                if country:
                    query += " WHERE country = %s"
                    params.append(country)
                query += f" ORDER BY updated_at DESC LIMIT {limit}"
                cur.execute(query, params)
                projects = [dict(row) for row in cur.fetchall()]
                cur.close()
                conn.close()
                logger.info(f"📊 Fetched {len(projects)} projects from database")
                return projects
            except Exception as e:
                logger.error(f"Database error: {e}, falling back to JSONL")

        # Tier 3: JSONL fallback
        if self._should_refresh_cache('projects', self.projects_file):
            self._cache['projects']['data'] = self._read_jsonl_file(self.projects_file, max_records=1000)
            self._cache['projects']['timestamp'] = datetime.now()
        projects = self._cache['projects']['data']
        if country:
            projects = [p for p in projects if p.get('country') == country]
        return projects[:limit]
    def get_projects_by_ids(self, project_ids: List[str]) -> List[Dict]:
        """Fetch specific projects by ID to avoid limit truncation during RAG."""
        if not project_ids:
            return []
            
        if self.use_db:
            try:
                conn = self._get_db_connection()
                cur = conn.cursor()
                format_strings = ','.join(['%s'] * len(project_ids))
                query = f"SELECT * FROM verra WHERE id IN ({format_strings}) OR project_id IN ({format_strings})"
                cur.execute(query, tuple(project_ids) + tuple(project_ids))
                projects = [dict(row) for row in cur.fetchall()]
                cur.close()
                conn.close()
                return projects
            except Exception as e:
                logger.error(f"Database error in get_projects_by_ids: {e}")
                
        all_projects = self.get_projects(limit=10000)
        return [p for p in all_projects if p.get('id') in project_ids or p.get('project_id') in project_ids]

    def get_finance(self, ticker: Optional[str] = None) -> List[Dict]:
        """Get finance data — gRPC → DB → JSONL fallback chain."""
        # Tier 1: gRPC
        if self.use_grpc:
            try:
                from grpc_client import get_finance_grpc
                data = get_finance_grpc(ticker=ticker)
                if data:
                    logger.info(f"⚡ gRPC: {len(data)} finance records")
                    return data
            except Exception as e:
                logger.warning(f"gRPC finance tier failed: {e}")

        # Tier 2: DB
        if self.use_db:
            try:
                conn = self._get_db_connection()
                cur  = conn.cursor()
                if ticker:
                    cur.execute("SELECT * FROM finance WHERE ticker = %s", (ticker,))
                else:
                    cur.execute("SELECT * FROM finance ORDER BY updated_at DESC")
                finance_data = [dict(row) for row in cur.fetchall()]
                cur.close()
                conn.close()
                logger.info(f"📊 Fetched {len(finance_data)} finance records from database")
                return finance_data
            except Exception as e:
                logger.error(f"Database error: {e}, falling back to JSONL")

        # Tier 3: JSONL fallback
        if self._should_refresh_cache('finance', self.finance_file):
            self._cache['finance']['data'] = self._read_jsonl_file(self.finance_file)
            self._cache['finance']['timestamp'] = datetime.now()
        finance_data = self._cache['finance']['data']
        if ticker:
            finance_data = [f for f in finance_data if f.get('ticker') == ticker]
        return finance_data
    
    def get_news(self, source: Optional[str] = None, limit: int = 250) -> List[Dict]:
        """Get news — gRPC → DB → JSONL fallback chain."""
        # Tier 1: gRPC
        if self.use_grpc:
            try:
                from grpc_client import get_news_grpc
                data = get_news_grpc(source=source, limit=limit)
                if data:
                    logger.info(f"⚡ gRPC: {len(data)} news articles")
                    return data
            except Exception as e:
                logger.warning(f"gRPC news tier failed: {e}")

        # Tier 2: DB
        if self.use_db:
            try:
                conn = self._get_db_connection()
                cur  = conn.cursor()
                query  = "SELECT * FROM news"
                params = []
                if source:
                    query += " WHERE source = %s"
                    params.append(source)
                query += f" ORDER BY published DESC LIMIT {limit}"
                cur.execute(query, params)
                news_data = [dict(row) for row in cur.fetchall()]
                cur.close()
                conn.close()
                logger.info(f"📊 Fetched {len(news_data)} news articles from database")
                return news_data
            except Exception as e:
                logger.error(f"Database error: {e}, falling back to JSONL")

        # Tier 3: JSONL fallback
        if self._should_refresh_cache('news', self.news_file):
            self._cache['news']['data'] = self._read_jsonl_file(self.news_file, max_records=250)
            self._cache['news']['timestamp'] = datetime.now()
        news_data = self._cache['news']['data']
        if source:
            news_data = [n for n in news_data if n.get('source') == source]
        return news_data[:limit]

    def get_pathway_enriched(self, entity_type: str = None, entity_id: str = None) -> List[Dict]:
        """Fetch Pathway-computed enriched signals from pathway_enriched table.
        Returns live signals computed by the Pathway streaming pipeline.
        analytics_service uses this to add pathway_computed=True badge in UI.
        """
        if not self.use_db:
            return []
        try:
            conn = self._get_db_connection()
            cur  = conn.cursor()
            query  = """
                SELECT entity_type, entity_id, metric_key, metric_value, extra_json, computed_at
                FROM pathway_enriched
                WHERE computed_at > NOW() - INTERVAL '15 minutes'
            """
            params = []
            if entity_type:
                query += " AND entity_type = %s"
                params.append(entity_type)
            if entity_id:
                query += " AND entity_id = %s"
                params.append(entity_id)
            query += " ORDER BY computed_at DESC"
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            conn.close()
            return rows
        except Exception as e:
            logger.warning(f"get_pathway_enriched() failed: {e}")
            return []
    
    def get_analytics(self) -> Dict[str, Any]:
        """Generate analytics from current data"""
        projects = self.get_projects(limit=1000)
        finance = self.get_finance()
        news = self.get_news(limit=250)
        
        total_supply = sum(p.get('available_credits', 0) for p in projects)
        total_price_sum = sum(p.get('price', 0) for p in projects if p.get('price'))
        avg_price = total_price_sum / len(projects) if projects else 0
        
        by_country = defaultdict(int)
        for p in projects:
            by_country[p.get('country', 'Unknown')] += 1
        
        by_category = defaultdict(int)
        for p in projects:
            by_category[p.get('category', 'Other')] += 1
        
        return {
            'projects': {
                'total': len(projects),
                'total_supply': total_supply,
                'avg_price': round(avg_price, 2),
                'by_country': dict(by_country),
                'by_category': dict(by_category),
                'top_countries': sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            'finance': {
                'total_tickers': len(finance),
                'avg_change': sum(f.get('change_percent', 0) for f in finance) / len(finance) if finance else 0
            },
            'news': {
                'total': len(news),
                'by_sentiment': {
                    'positive': len([n for n in news if n.get('sentiment') == 'Positive']),
                    'negative': len([n for n in news if n.get('sentiment') == 'Negative']),
                    'neutral': len([n for n in news if n.get('sentiment') == 'Neutral'])
                }
            },
            'last_update': datetime.now().isoformat()
        }
    
    def has_changes(self) -> bool:
        """Check if any data has changed since last read.
        When DB is available, polls MAX(updated_at/published) per table every 5s.
        When file-based, checks file modification times.
        """
        if not self.use_db:
            # File-based fallback (original logic)
            files_to_check = [
                ('projects', self.projects_file),
                ('finance',  self.finance_file),
                ('news',     self.news_file),
            ]
            for cache_key, filepath in files_to_check:
                if self._file_changed(filepath, cache_key):
                    return True
            return False

        # DB-based: poll every 5 seconds max to avoid hammering Postgres
        now = time.time()
        if now - self._last_db_poll < 5.0:
            return False
        self._last_db_poll = now

        try:
            conn = self._get_db_connection()
            cur  = conn.cursor()

            changed = False
            checks = [
                ('news',    'MAX(published)',   '_last_news_ts'),
                ('finance', 'MAX(updated_at)',  '_last_finance_ts'),
                ('verra',   'MAX(updated_at)',  '_last_verra_ts'),
            ]
            for table, agg, attr in checks:
                try:
                    cur.execute(f"SELECT {agg} FROM {table}")
                    row = cur.fetchone()
                    val = str(row[0]) if row and row[0] else None
                    prev = getattr(self, attr)
                    if val != prev:
                        setattr(self, attr, val)
                        changed = True
                        logger.debug(f"🔄 Change detected in {table}: {prev} → {val}")
                except Exception as te:
                    logger.debug(f"Change check for {table} failed: {te}")

            cur.close()
            conn.close()
            return changed
        except Exception as e:
            logger.error(f"has_changes() DB poll failed: {e}")
            return False
    
    def search_projects(self, query: str, limit: int = 50) -> List[Dict]:
        """Search projects by name, country, or category"""
        projects = self.get_projects()
        query_lower = query.lower()
        
        results = [
            p for p in projects
            if query_lower in p.get('project_name', '').lower()
            or query_lower in p.get('country', '').lower()
            or query_lower in p.get('category', '').lower()
            or query_lower in p.get('description', '').lower()
        ]
        
        return results[:limit]
