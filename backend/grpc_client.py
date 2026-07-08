"""
gRPC Client — Flask backend's connection to the carbon_pathway gRPC server.

Data flow:
  Flask → PathwayReader.get_*() → grpc_client → carbon_pathway:50051
                                               ↓
                                         gRPC Servicer reads JSONL / DB
                                         (enriched by Pathway pipeline)

If the gRPC server is unreachable (e.g. Pathway crashed), all functions
return empty lists — PathwayReader then falls back to direct DB queries
so the API never goes down.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# gRPC host/port from env (set in docker-compose backend service)
GRPC_HOST = os.getenv("PATHWAY_GRPC_HOST", "carbon_pathway")
GRPC_PORT = os.getenv("PATHWAY_GRPC_PORT", "50051")
GRPC_ADDR = f"{GRPC_HOST}:{GRPC_PORT}"
GRPC_TIMEOUT = 4  # seconds — keep it tight so Flask doesn't stall

# Lazy import of generated stubs (they live in the carbon-intelligence/server dir)
_stub_dir = os.path.join(os.path.dirname(__file__), "carbon-intelligence", "server")
if _stub_dir not in sys.path:
    sys.path.insert(0, _stub_dir)

try:
    import grpc
    import carbon_service_pb2 as pb2
    import carbon_service_pb2_grpc as pb2_grpc
    GRPC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"gRPC stubs not importable: {e} — gRPC tier disabled")
    GRPC_AVAILABLE = False


def _channel():
    """Create a short-lived insecure gRPC channel."""
    return grpc.insecure_channel(GRPC_ADDR)


def test_grpc_connection() -> bool:
    """Return True if the gRPC server is reachable (used by PathwayReader.__init__)."""
    if not GRPC_AVAILABLE:
        return False
    try:
        with _channel() as ch:
            stub = pb2_grpc.CarbonServiceStub(ch)
            # GetProjects with empty query is the lightest call
            stub.GetProjects(pb2.ProjectQuery(country=""), timeout=2)
        logger.info(f"✅ gRPC connection to {GRPC_ADDR} verified")
        return True
    except Exception as e:
        logger.warning(f"gRPC not reachable at {GRPC_ADDR}: {e}")
        return False


def get_projects_grpc(country: str = None, limit: int = 1000) -> list:
    """
    Fetch projects from carbon_pathway via gRPC.
    Returns list of dicts, or [] on any failure.
    """
    if not GRPC_AVAILABLE:
        return []
    try:
        with _channel() as ch:
            stub = pb2_grpc.CarbonServiceStub(ch)
            resp = stub.GetProjects(
                pb2.ProjectQuery(country=country or ""),
                timeout=GRPC_TIMEOUT
            )
            result = [
                {
                    "project_id":       item.project_id,
                    "project_name":     item.project_name,
                    "registry_status":  item.registry_status,
                    "country":          item.country,
                    "vintage":          item.vintage,
                    "available_credits": int(item.supply),
                    "price":            0.0,   # enriched from pathway_enriched later
                }
                for item in resp.items
            ]
            logger.info(f"⚡ gRPC GetProjects: {len(result)} records")
            return result[:limit]
    except Exception as e:
        logger.warning(f"gRPC GetProjects failed ({e}), falling back to DB")
        return []


def get_news_grpc(source: str = None, limit: int = 250) -> list:
    """
    Fetch news from carbon_pathway via gRPC.
    Returns list of dicts, or [] on failure.
    """
    if not GRPC_AVAILABLE:
        return []
    try:
        with _channel() as ch:
            stub = pb2_grpc.CarbonServiceStub(ch)
            resp = stub.GetNews(
                pb2.NewsQuery(source=source or ""),
                timeout=GRPC_TIMEOUT
            )
            result = [
                {
                    "id":        item.guid,
                    "title":     item.title,
                    "link":      item.link,
                    "published": item.published,
                    "source":    item.source,
                    "summary":   item.summary,
                    "sentiment": "Neutral",  # gRPC proto doesn't carry sentiment yet
                }
                for item in resp.items
            ]
            logger.info(f"⚡ gRPC GetNews: {len(result)} records")
            return result[:limit]
    except Exception as e:
        logger.warning(f"gRPC GetNews failed ({e}), falling back to DB")
        return []


def get_finance_grpc(ticker: str = None) -> list:
    """
    Fetch finance data from carbon_pathway via gRPC.
    Returns list of dicts, or [] on failure.
    """
    if not GRPC_AVAILABLE:
        return []
    try:
        with _channel() as ch:
            stub = pb2_grpc.CarbonServiceStub(ch)
            resp = stub.GetFinanceData(
                pb2.FinanceQuery(ticker=ticker or ""),
                timeout=GRPC_TIMEOUT
            )
            result = [
                {
                    "ticker":         item.ticker,
                    "price":          item.price,
                    "stock_price":    item.price,
                    "volume":         item.volume,
                    "market_cap":     str(item.market_cap),
                    "change_percent": item.change_percent,
                    "timestamp":      item.timestamp,
                }
                for item in resp.items
            ]
            logger.info(f"⚡ gRPC GetFinanceData: {len(result)} records")
            return result
    except Exception as e:
        logger.warning(f"gRPC GetFinanceData failed ({e}), falling back to DB")
        return []


def get_project_detail_grpc(project_id: str) -> dict:
    """
    Fetch a single project's full detail via gRPC.
    Returns dict, or {} on failure.
    """
    if not GRPC_AVAILABLE:
        return {}
    try:
        with _channel() as ch:
            stub = pb2_grpc.CarbonServiceStub(ch)
            resp = stub.GetProjectDetail(
                pb2.ProjectDetailQuery(project_id=project_id),
                timeout=GRPC_TIMEOUT
            )
            p = resp.project
            return {
                "project_id":      p.project_id,
                "project_name":    p.project_name,
                "registry_status": p.registry_status,
                "country":         p.country,
                "vintage":         p.vintage,
                "available_credits": int(p.supply),
                "project_summary": p.project_summary,
                "project_link":    p.project_link,
                "source":          p.source,
            }
    except Exception as e:
        logger.warning(f"gRPC GetProjectDetail failed ({e}), falling back to DB")
        return {}
