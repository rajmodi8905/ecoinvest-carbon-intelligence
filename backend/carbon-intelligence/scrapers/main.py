import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import os
from finance_scraper import run_finance_scraper
from news_scraper import run_news_scraper
from verra_scraper import run_verra_scraper

print("🔥 Scraper service started")

# Top 20 famous stocks/ETFs
COMPANIES = [
    "TSLA",   
    "MSFT",   
    "GOOGL",  
    "AAPL",   
    "AMZN",   
    "ENPH",   
    "PLUG",   
    "FCEL",   
    "BLNK",   
    "CHPT",   
    "NEE",    
    "RUN",    
    "SEDG",   
    "ORSTED", 
    "EQNR",   
    "ICLN",   
    "TAN",    
    "QCLN",   
    "KRBN",
    "BEPC",
]

# Configurable scrape interval (in seconds)
SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", 30))

CARBON_KEYWORDS = [
    "carbon credits",
    "carbon offset",
    "carbon trading",
    "carbon market",
    "emissions trading",
    "carbon neutral",
    "net zero",
    "carbon sequestration",
    "carbon capture",
    "CCUS",
    "renewable energy credits",
    "REC",
    "voluntary carbon market",
    "compliance carbon market",
    "carbon allowances",
    "cap and trade",
]

print(f"📊 Tracking {len(COMPANIES)} companies/tickers")
print(f"🔍 Monitoring {len(CARBON_KEYWORDS)} carbon-related keywords")


def get_connection():
    while True:
        try:
            conn = psycopg2.connect(
                dbname="carbon_intel",
                user="carbon",
                password="carbonpw",
                host="postgres",
                port=5432,
            )
            print("✅ Connected to PostgreSQL")
            return conn
        except psycopg2.OperationalError:
            print("⏳ Waiting for PostgreSQL...")
            time.sleep(2)


conn = get_connection()

def run_continuous_scraper(scraper_name, scraper_func, interval_seconds, *args):
    """Run a scraper task continuously in its own isolated thread."""
    print(f"🚀 Starting continuous loop for {scraper_name} scraper (interval: {interval_seconds}s)")
    while True:
        try:
            print(f"📌 [START] {scraper_name} scraper...")
            scraper_func(*args)
            print(f"✅ [DONE] {scraper_name} scraper. Sleeping for {interval_seconds}s...")
        except Exception as e:
            print(f"❌ [ERROR] {scraper_name} scraper failed: {e}. Sleeping for {interval_seconds}s...")
        
        print("\n" + "="*60)
        print(f"✨ Scraper cycle complete: {completed}/3 successful")
        print(f"⏳ Sleeping for {SCRAPE_INTERVAL_SECONDS} seconds...")
        print("="*60 + "\n")
        time.sleep(SCRAPE_INTERVAL_SECONDS)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Starting independent scraper microservices...")
    print("="*60)
    
    threads = []
    
    # 1. News Scraper: Runs every 10 seconds (Extremely fast, highly concurrent)
    t_news = threading.Thread(
        target=run_continuous_scraper, 
        args=("News", run_news_scraper, 10, CARBON_KEYWORDS, COMPANIES, None),
        daemon=True
    )
    threads.append(t_news)
    
    # 2. Finance Scraper: Unpaused & Optimized
    t_finance = threading.Thread(
        target=run_continuous_scraper, 
        args=("Finance", run_finance_scraper, 10, None, COMPANIES),
        daemon=True
    )
    threads.append(t_finance)
    
    # 3. Verra Scraper: Temporarily Paused
    # t_verra = threading.Thread(
    #     target=run_continuous_scraper, 
    #     args=("Verra", run_verra_scraper, 60, None),
    #     daemon=True
    # )
    # threads.append(t_verra)
    
    # Start all independent threads
    for t in threads:
        t.start()
        
    # Keep the main process alive forever
    while True:
        time.sleep(3600)
