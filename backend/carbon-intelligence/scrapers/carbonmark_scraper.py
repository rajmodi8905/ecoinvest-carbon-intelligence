"""
Carbonmark Scraper — REST API v19

Uses the official Carbonmark REST API (https://v19.api.carbonmark.com)
No API key required for read endpoints.

Endpoints used:
  GET /carbonProjects?limit=N  → projects with price + supply stats
  GET /prices?limit=N           → active marketplace listing prices

Data stored:
  - carbonmark table: project_id, project_name, vintage, amount (best-ask price/tonne), project_link
"""

import time
import random
import psycopg2
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Official Carbonmark REST API — free, no key required for read endpoints
CARBONMARK_API_BASE = "https://v19.api.carbonmark.com"

# Headers to identify ourselves politely
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CarbonIntel-Research/1.0 (carbon market intelligence platform)",
}


def get_session_with_retries():
    """Create requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_carbonmark_projects(session, limit=200):
    """
    Fetch projects from the official Carbonmark REST API v19.
    Returns list of project dicts with: key, projectID, name, price, stats, country, registry, vintages
    """
    projects = []
    offset = 0
    batch_size = min(limit, 100)  # API max per page

    print(f"📡 Fetching up to {limit} projects from Carbonmark REST API v19...")

    while len(projects) < limit:
        try:
            url = f"{CARBONMARK_API_BASE}/carbonProjects"
            params = {
                "limit": batch_size,
                "offset": offset,
            }
            resp = session.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            total = data.get("itemsCount", 0)

            if not items:
                break

            projects.extend(items)
            offset += len(items)

            print(f"   ✓ Fetched {len(projects)}/{min(limit, total)} projects")

            if offset >= total or len(projects) >= limit:
                break

            # Polite rate limiting
            time.sleep(0.3)

        except Exception as e:
            print(f"❌ Carbonmark API fetch failed at offset {offset}: {e}")
            break

    print(f"✅ Total Carbonmark projects fetched: {len(projects)}")
    return projects[:limit]


def fetch_carbonmark_prices(session, limit=500):
    """
    Fetch active marketplace listing prices from Carbonmark v19 /prices endpoint.
    Returns dict: {project_key: best_ask_price_usd}
    """
    price_map = {}

    print(f"📡 Fetching active listing prices from Carbonmark API...")

    try:
        url = f"{CARBONMARK_API_BASE}/prices"
        params = {"limit": limit}
        resp = session.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        price_list = resp.json()

        if isinstance(price_list, list):
            for item in price_list:
                # Each item has: sourceId, type, purchasePrice, baseUnitPrice, supply, listing...
                proj_key = None
                # Extract project key from nested listing.project.key or creditId
                listing_info = item.get("listing", {})
                if listing_info:
                    proj = listing_info.get("project", {})
                    if proj:
                        proj_key = proj.get("key") or proj.get("id")

                if not proj_key:
                    # Try creditId parsing e.g. "VCS-191-2008"
                    credit_id = item.get("creditId", "")
                    if credit_id:
                        parts = credit_id.split("-")
                        if len(parts) >= 2:
                            proj_key = f"{parts[0]}-{parts[1]}"

                if proj_key:
                    purchase_price = float(item.get("purchasePrice", 0) or 0)
                    supply = float(item.get("supply", 0) or 0)
                    # Keep best ask (lowest price with supply)
                    if supply > 0 and purchase_price > 0:
                        if proj_key not in price_map or purchase_price < price_map[proj_key]["price"]:
                            price_map[proj_key] = {
                                "price": purchase_price,
                                "supply": supply,
                            }

        print(f"   ✓ Got prices for {len(price_map)} projects")

    except Exception as e:
        print(f"⚠️ Carbonmark prices fetch failed: {e}")

    return price_map


def run_carbonmark_scraper(conn=None):
    """
    Scrape carbon credit projects and prices from the Carbonmark REST API v19.
    No API key required — fully public read endpoints.
    """
    own_conn = False
    if conn is None:
        import os
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "carbon_intel"),
            user=os.getenv("DB_USER", "carbon"),
            password=os.getenv("DB_PASSWORD", "carbonpw"),
            host=os.getenv("DB_HOST", "postgres"),
            port=int(os.getenv("DB_PORT", 5432)),
        )
        own_conn = True

    cur = conn.cursor()
    print("📡 Starting Carbonmark scraper (REST API v19 — no key required)...")

    session = get_session_with_retries()

    # 1. Fetch projects
    projects = fetch_carbonmark_projects(session, limit=200)

    if not projects:
        print("❌ No projects fetched from Carbonmark API — check network")
        cur.close()
        if own_conn:
            conn.close()
        return

    # 2. Fetch live listing prices
    price_map = fetch_carbonmark_prices(session, limit=500)
    print(f"📊 Processing {len(projects)} Carbonmark projects...")

    stored = 0
    for project in projects:
        try:
            # Use 'key' (e.g. "VCS-191") as the primary project identifier
            project_key = project.get("key") or project.get("projectID", "")
            project_id = project.get("projectID", "")
            if not project_key:
                continue

            project_name = project.get("name", "Unknown Project")
            country = project.get("country", "")
            registry = project.get("registry", "VCS")

            # Vintages: list of strings like ["2008", "2009"]
            vintages = project.get("vintages", [])
            vintage = None
            if vintages:
                try:
                    vintage = int(vintages[-1])  # Use most recent vintage
                except (ValueError, TypeError):
                    vintage = None

            # Price: the project-level price (lowest across listings)
            price_str = project.get("price", "0") or "0"
            try:
                project_price = float(price_str)
            except (ValueError, TypeError):
                project_price = 0.0

            # Override with live best-ask if available
            live_price = price_map.get(project_key, {})
            if live_price and live_price.get("price", 0) > 0:
                amount = live_price["price"]
            elif project_price > 0:
                amount = project_price
            else:
                amount = 0.0

            # Total supply (tonnes)
            stats = project.get("stats", {}) or {}
            total_supply = float(stats.get("totalSupply", 0) or 0)
            total_retired = float(stats.get("totalRetired", 0) or 0)

            description = (
                project.get("long_description")
                or project.get("short_description")
                or project.get("description")
                or f"Carbon credit project: {project_name}"
            )
            if isinstance(description, list):
                # Portable text block format — flatten to string
                description = " ".join(
                    child.get("text", "")
                    for block in description
                    for child in block.get("children", [])
                ).strip()

            project_summary = str(description)[:500]
            project_link = f"https://www.carbonmark.com/projects/{project_key}"

            cur.execute("""
                INSERT INTO carbonmark (project_id, project_name, vintage, amount, project_summary, project_link)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id) DO UPDATE SET
                    project_name = EXCLUDED.project_name,
                    vintage = EXCLUDED.vintage,
                    amount = EXCLUDED.amount,
                    project_summary = EXCLUDED.project_summary,
                    project_link = EXCLUDED.project_link,
                    updated_at = CURRENT_TIMESTAMP
            """, (project_key, project_name, vintage, amount, project_summary, project_link))

            conn.commit()
            stored += 1

        except Exception as e:
            print(f"⚠️ Error storing project {project.get('name', 'unknown')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    if own_conn:
        conn.close()

    print(f"✅ Carbonmark: Stored {stored}/{len(projects)} projects "
          f"({len(price_map)} had live listing prices)")
