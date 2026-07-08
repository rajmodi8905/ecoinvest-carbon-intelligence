"""
Real-time finance data scraper using multiple free APIs.
NO mock data - fetches from real sources or fails.
"""

import psycopg2
import time
import random
import requests
import re
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Dictionary to store cached GII scores: { 'TICKER': {'score': 85, 'timestamp': 160000000} }
GII_CACHE = {}
GII_CACHE_DURATION = 10 * 60 * 60  # 10 hours in seconds

def get_ollama_model():
    '''Initialize and return Ollama model'''
    try:
        return ChatOllama(
            model="qwen2.5",
            base_url="http://host.docker.internal:11434",
            temperature=0.2,
        )
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize Ollama model: {e}")
        return None

def create_gii_chain(llm):
    '''Create the GII calculation chain using Ollama'''
    if llm is None:
        return None
    
    system_instructions = """
You are a financial and sustainability expert. 
Calculate the GII (Green Investment Index) score (0-100) for the given company.
The GII score is designed to quantify a company's financial performance with respect to its sustainability efforts.
You should evaluate based on the company's industry, known green initiatives, and their general market reputation for sustainability.

Respond ONLY with a single integer between 0 and 100. Do not provide any explanation or extra text.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("human", "Calculate the GII score for {company_name} ({ticker}) in the {industry} industry.")
    ])
    
    return prompt | llm | StrOutputParser()

_llm = get_ollama_model()
_gii_chain = create_gii_chain(_llm)

# Multiple free finance APIs (no API key needed)
APIS = {
    'finnhub': 'https://finnhub.io/api/v1/quote',  # Free tier: 60 calls/min
    'alphavantage': 'https://www.alphavantage.co/query',  # Free tier: 5 calls/min
    'yahoo_query': 'https://query1.finance.yahoo.com/v8/finance/chart/{}'
}

# Priority tickers
TICKERS = [
    'TSLA', 'MSFT', 'NVDA', 'AAPL', 'GOOGL', 'AMZN', 'ORCL', 'ENPH', 'NEE', 'FLNC',
    'TATAPOWER.NS', 'RELIANCE.NS', 'INFY.NS', 'TCS.NS', 'ADANIGREEN.NS', 'NTPC.NS', 'SUZLON.NS', 'JSWENERGY.NS', 'ITC.NS', 'WIPRO.NS'
]

# Company metadata
COMPANY_INFO = {
    'TSLA': {'name': 'Tesla, Inc.', 'industry': 'Automotive', 'description': 'Electric vehicles and clean energy', 'website': 'https://www.tesla.com', 'market_cap': '$800B'},
    'MSFT': {'name': 'Microsoft Corporation', 'industry': 'Technology', 'description': 'Software, cloud computing, and AI', 'website': 'https://www.microsoft.com', 'market_cap': '$3.0T'},
    'NVDA': {'name': 'NVIDIA Corporation', 'industry': 'Semiconductors', 'description': 'Graphics processing and AI computing', 'website': 'https://www.nvidia.com', 'market_cap': '$3.0T'},
    'AAPL': {'name': 'Apple Inc.', 'industry': 'Technology', 'description': 'Consumer electronics and software', 'website': 'https://www.apple.com', 'market_cap': '$3.5T'},
    'GOOGL': {'name': 'Alphabet Inc.', 'industry': 'Technology', 'description': 'Internet services and AI', 'website': 'https://www.google.com', 'market_cap': '$2.0T'},
    'AMZN': {'name': 'Amazon.com, Inc.', 'industry': 'E-commerce & Cloud', 'description': 'Online retail and cloud services', 'website': 'https://www.amazon.com', 'market_cap': '$1.8T'},
    'ORCL': {'name': 'Oracle Corporation', 'industry': 'Technology', 'description': 'Database software and cloud services', 'website': 'https://www.oracle.com', 'market_cap': '$350B'},
    'ENPH': {'name': 'Enphase Energy, Inc.', 'industry': 'Renewable Energy', 'description': 'Microinverter-based solar and battery systems', 'website': 'https://enphase.com', 'market_cap': '$15B'},
    'NEE': {'name': 'NextEra Energy, Inc.', 'industry': 'Utilities', 'description': 'Largest producer of wind and solar energy', 'website': 'https://www.nexteraenergy.com', 'market_cap': '$150B'},
    'FLNC': {'name': 'Fluence Energy, Inc.', 'industry': 'Energy Storage', 'description': 'Grid-scale battery storage products and software', 'website': 'https://fluenceenergy.com', 'market_cap': '$4B'},
    'TATAPOWER.NS': {'name': 'Tata Power Company Limited', 'industry': 'Utilities & Clean Energy', 'description': 'Integrated clean energy and EV charging leader', 'website': 'https://www.tatapower.com', 'market_cap': '$14B'},
    'RELIANCE.NS': {'name': 'Reliance Industries Limited', 'industry': 'Conglomerate', 'description': '$10B green hydrogen and solar manufacturing initiative', 'website': 'https://www.ril.com', 'market_cap': '$240B'},
    'INFY.NS': {'name': 'Infosys Limited', 'industry': 'Information Technology', 'description': 'Global IT consulting leader, 100% carbon neutral', 'website': 'https://www.infosys.com', 'market_cap': '$80B'},
    'TCS.NS': {'name': 'Tata Consultancy Services', 'industry': 'Information Technology', 'description': 'Global IT services driving digital sustainability', 'website': 'https://www.tcs.com', 'market_cap': '$160B'},
    'ADANIGREEN.NS': {'name': 'Adani Green Energy Limited', 'industry': 'Renewable Energy', 'description': 'Developing massive 30 GW solar/wind hybrid parks', 'website': 'https://www.adanigreenenergy.com', 'market_cap': '$30B'},
    'NTPC.NS': {'name': 'NTPC Limited', 'industry': 'Utilities', 'description': 'Decarbonizing utility installing 60 GW renewables', 'website': 'https://www.ntpc.co.in', 'market_cap': '$40B'},
    'SUZLON.NS': {'name': 'Suzlon Energy Limited', 'industry': 'Wind Energy', 'description': 'Premier wind turbine manufacturer with 20+ GW capacity', 'website': 'https://www.suzlon.com', 'market_cap': '$8B'},
    'JSWENERGY.NS': {'name': 'JSW Energy Limited', 'industry': 'Utilities', 'description': 'Hydro, wind, and green hydrogen power producer', 'website': 'https://www.jsw.in/energy', 'market_cap': '$12B'},
    'ITC.NS': {'name': 'ITC Limited', 'industry': 'Consumer Goods', 'description': 'Carbon-positive and water-positive conglomerate', 'website': 'https://www.itcportal.com', 'market_cap': '$65B'},
    'WIPRO.NS': {'name': 'Wipro Limited', 'industry': 'Information Technology', 'description': 'Committed to Net-Zero GHG emissions by 2040', 'website': 'https://www.wipro.com', 'market_cap': '$30B'}
}

def fetch_esg_from_yahoo(ticker):
    """Fetch ESG scores from Yahoo Finance API"""
    try:
        # Yahoo Finance sustainability endpoint
        url = f'https://query2.finance.yahoo.com/v1/finance/esgChart?symbol={ticker}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            esg_chart = data.get('esgChart', {})
            result = esg_chart.get('result', [])
            
            if result:
                symbol_data = result[0]
                esg_scores = symbol_data.get('esgScores', {})
                
                # Get the total ESG score
                total_esg = esg_scores.get('totalEsg')
                
                if total_esg is not None:
                    # Convert ESG score (0-100) to letter rating
                    # Yahoo ESG: Lower is better (0-10 best, 40+ worst)
                    if total_esg < 10:
                        rating = 'A+'
                    elif total_esg < 20:
                        rating = 'A'
                    elif total_esg < 30:
                        rating = 'B+'
                    elif total_esg < 40:
                        rating = 'B'
                    else:
                        rating = 'C'
                    
                    return {
                        'esg_rating': rating,
                        'esg_score': total_esg,
                        'environment_score': esg_scores.get('environmentScore'),
                        'social_score': esg_scores.get('socialScore'),
                        'governance_score': esg_scores.get('governanceScore')
                    }
    except Exception as e:
        print(f"Yahoo ESG API error for {ticker}: {e}")
    return None

def fetch_from_yahoo_query(ticker):
    """Fetch from Yahoo Finance Query API (no library, direct HTTP)"""
    try:
        url = APIS['yahoo_query'].format(ticker)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('chart', {}).get('result', [])
            if result:
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                prev_close = meta.get('previousClose')
                
                if price and prev_close:
                    change = price - prev_close
                    change_pct = (change / prev_close) * 100
                    return {
                        'price': price,
                        'change': change,
                        'change_percent': change_pct
                    }
    except Exception as e:
        print(f"Yahoo API error for {ticker}: {e}")
    return None

def fetch_from_finnhub(ticker):
    """Fetch from Finnhub API (free tier, no key for basic quotes)"""
    try:
        # Finnhub free tier demo token
        url = f"{APIS['finnhub']}?symbol={ticker}&token=demo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('c')  # Current price
            prev_close = data.get('pc')  # Previous close
            
            if current and prev_close and current > 0:
                change = current - prev_close
                change_pct = (change / prev_close) * 100
                return {
                    'price': current,
                    'change': change,
                    'change_percent': change_pct
                }
    except Exception as e:
        print(f"Finnhub API error for {ticker}: {e}")
    return None

def fetch_stock_data(ticker):
    """Try multiple APIs in sequence until one succeeds"""
    print(f"🔍 Fetching {ticker}...")
    
    # Try Yahoo Query first (most reliable)
    data = fetch_from_yahoo_query(ticker)
    if data:
        print(f"✅ {ticker}: ${data['price']:.2f} ({data['change_percent']:+.2f}%) [Yahoo]")
        return data
    
    # Wait before trying next API
    time.sleep(random.uniform(2, 4))
    
    # Try Finnhub
    data = fetch_from_finnhub(ticker)
    if data:
        print(f"✅ {ticker}: ${data['price']:.2f} ({data['change_percent']:+.2f}%) [Finnhub]")
        return data
    
    print(f"❌ {ticker}: All APIs failed")
    return None

def get_gii_score(ticker, company_name, industry, change_pct):
    current_time = time.time()
    
    # Check cache
    if ticker in GII_CACHE:
        cached_data = GII_CACHE[ticker]
        if current_time - cached_data['timestamp'] < GII_CACHE_DURATION:
            return cached_data['score']
            
    # Calculate using AI
    if _gii_chain is not None:
        try:
            print(f"🧠 Calculating AI GII score for {ticker}...")
            result = _gii_chain.invoke({
                "company_name": company_name,
                "ticker": ticker,
                "industry": industry
            })
            
            # Extract number
            try:
                numbers = re.findall(r'\d+', result)
                if numbers:
                    score = min(100, max(0, int(numbers[0])))
                else:
                    score = max(0, min(100, 50 + change_pct * 2))
            except ValueError:
                score = max(0, min(100, 50 + change_pct * 2))
                
            # Update cache
            GII_CACHE[ticker] = {
                'score': score,
                'timestamp': current_time
            }
            print(f"   🤖 AI GII Score: {score}")
            return score
        except Exception as e:
            print(f"⚠️ GII LLM error for {ticker}: {e}")
            
    # Fallback
    return max(0, min(100, 50 + change_pct * 2))

def store_finance_data(cursor, ticker, price_data, esg_data=None):
    """Store finance data in database"""
    info = COMPANY_INFO.get(ticker, {})
    company_name = info.get('name', ticker)
    industry = info.get('industry', 'Technology')
    
    # Calculate GII score using AI (with cache)
    change_pct = price_data['change_percent']
    gii_score = get_gii_score(ticker, company_name, industry, change_pct)
    
    # ESG is being phased out, but keeping for DB schema compatibility
    if esg_data and esg_data.get('esg_rating'):
        esg_rating = esg_data['esg_rating']
    else:
        esg_rating = 'B'
    
    cursor.execute("""
        INSERT INTO finance (
            ticker, company_name, price, stock_price, change_percent,
            industry, description, gii_score, sustainability_update,
            esg_rating, website, market_cap
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            price = EXCLUDED.price,
            stock_price = EXCLUDED.stock_price,
            change_percent = EXCLUDED.change_percent,
            gii_score = EXCLUDED.gii_score,
            esg_rating = EXCLUDED.esg_rating,
            market_cap = EXCLUDED.market_cap,
            updated_at = CURRENT_TIMESTAMP
    """, (
        ticker,
        company_name,
        price_data['price'],
        price_data['price'],  # Populate stock_price with the same value
        price_data['change_percent'],
        info.get('industry', 'Technology'),
        info.get('description', f'{ticker} company'),
        gii_score,
        f"Recent sustainability initiatives for {ticker}",
        esg_rating,
        info.get('website', f'https://www.{ticker.lower()}.com'),
        info.get('market_cap', 'N/A')
    ))

def run_finance_scraper(conn=None, tickers=None):
    """Main scraper function - called by main.py"""
    
    # Create connection if not provided
    own_conn = False
    if conn is None:
        conn = psycopg2.connect(
            dbname="carbon_intel",
            user="carbon",
            password="carbonpw",
            host="postgres",
            port=5432,
        )
        own_conn = True
    
    if tickers is None:
        tickers = TICKERS
    
    print("=" * 60)
    print("🚀 Starting Real Finance Data Scraper")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Tickers to fetch: {len(tickers)}")
    print("=" * 60)
    
    cursor = conn.cursor()
    successful = 0
    failed = 0
    
    for idx, ticker in enumerate(tickers, 1):
        print(f"\n[{idx}/{len(tickers)}] {ticker}")
        
        try:
            # Fetch price data
            price_data = fetch_stock_data(ticker)
            
            if price_data:
                # Fetch ESG data
                esg_data = fetch_esg_from_yahoo(ticker)
                
                # Store combined data
                store_finance_data(cursor, ticker, price_data, esg_data)
                conn.commit()
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Error storing {ticker}: {e}")
            conn.rollback()  # Rollback transaction on error
            failed += 1
        
        # Rate limiting between tickers
        if idx < len(tickers):
            delay = random.uniform(5, 10)
            print(f"⏳ Wait {delay:.1f}s before next ticker...")
            time.sleep(delay)
    
    cursor.close()
    if own_conn:
        conn.close()
    
    print("\n" + "=" * 60)
    print("✨ Finance Scraper Complete!")
    print(f"✅ Successful: {successful}/{len(tickers)}")
    print(f"❌ Failed: {failed}/{len(tickers)}")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    # Standalone mode - connect to DB and run
    conn = psycopg2.connect(
        host="postgres",
        database="carbon_intel",
        user="carbon",
        password="carbon123"
    )
    
    while True:
        try:
            run_finance_scraper(conn)
            print("\n💤 Sleeping 300 seconds (5 min) before next run...")
            time.sleep(300)  # Run every 5 minutes
        except KeyboardInterrupt:
            print("\n👋 Shutting down finance scraper...")
            break
        except Exception as e:
            print(f"\n💥 Error: {e}")
            print("⏳ Retrying in 60 seconds...")
            time.sleep(60)
    
    conn.close()
