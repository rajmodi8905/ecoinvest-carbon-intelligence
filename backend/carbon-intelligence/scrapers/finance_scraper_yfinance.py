import time
import random

import psycopg2
import yfinance as yf

conn = psycopg2.connect(
    dbname="carbon_intel",
    user="carbon",
    password="carbonpw",
    host="postgres",
    port=5432,
)
cur = conn.cursor()

# Company metadata matching frontend format
COMPANY_METADATA = {
    # US Titans
    "TSLA": {
        "name": "Tesla, Inc.",
        "industry": "Automotive & Energy",
        "description": "Leading electric vehicle manufacturer and clean energy company producing EVs, battery energy storage systems, and solar products.",
        "gii_score": 89,
        "sustainability_update": "Announced plans to power all Gigafactories with 100% renewable energy by 2026.",
        "esg_rating": "A",
        "website": "https://www.tesla.com",
        "market_cap_fallback": 800000000000
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "industry": "Technology",
        "description": "Global technology leader providing cloud computing, software, devices, and services.",
        "gii_score": 92,
        "sustainability_update": "Achieved 100% renewable energy in all data centers globally.",
        "esg_rating": "AAA",
        "website": "https://www.microsoft.com",
        "market_cap_fallback": 3000000000000
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "industry": "Semiconductors",
        "description": "Pioneer in GPU technology and AI computing platforms.",
        "gii_score": 85,
        "sustainability_update": "Launched Earth-2 climate digital twin initiative.",
        "esg_rating": "AA",
        "website": "https://www.nvidia.com",
        "market_cap_fallback": 3000000000000
    },
    "AAPL": {
        "name": "Apple Inc.",
        "industry": "Technology",
        "description": "Designer and manufacturer of consumer electronics, software, and online services.",
        "gii_score": 94,
        "sustainability_update": "Launched first carbon-neutral product line with Apple Watch Series 9.",
        "esg_rating": "AAA",
        "website": "https://www.apple.com",
        "market_cap_fallback": 3500000000000
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "industry": "Technology",
        "description": "Technology conglomerate specializing in internet services and products.",
        "gii_score": 90,
        "sustainability_update": "Operating on 24/7 carbon-free energy in multiple data centers.",
        "esg_rating": "AA",
        "website": "https://about.google",
        "market_cap_fallback": 2000000000000
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "industry": "E-commerce & Cloud",
        "description": "Global e-commerce and cloud computing giant.",
        "gii_score": 82,
        "sustainability_update": "Committed to net-zero carbon by 2040 with 100,000+ electric delivery vehicles.",
        "esg_rating": "A",
        "website": "https://www.amazon.com",
        "market_cap_fallback": 1800000000000
    },
    "ORCL": {
        "name": "Oracle Corporation",
        "industry": "Technology",
        "description": "Enterprise software and cloud infrastructure provider.",
        "gii_score": 81,
        "sustainability_update": "Surpassed 90% renewable energy across global operations.",
        "esg_rating": "A",
        "website": "https://www.oracle.com",
        "market_cap_fallback": 350000000000
    },
    "ENPH": {
        "name": "Enphase Energy, Inc.",
        "industry": "Renewable Energy",
        "description": "Global energy technology company supplying microinverter-based solar and battery systems.",
        "gii_score": 95,
        "sustainability_update": "Shipped over 70 million residential microinverters globally.",
        "esg_rating": "AAA",
        "website": "https://enphase.com",
        "market_cap_fallback": 15000000000
    },
    "NEE": {
        "name": "NextEra Energy, Inc.",
        "industry": "Utilities & Energy",
        "description": "Largest producer of wind and solar energy in the world.",
        "gii_score": 91,
        "sustainability_update": "Expanding battery storage capacity by 3 GW across North America.",
        "esg_rating": "AAA",
        "website": "https://www.nexteraenergy.com",
        "market_cap_fallback": 150000000000
    },
    "FLNC": {
        "name": "Fluence Energy, Inc.",
        "industry": "Energy Storage",
        "description": "Market leader in energy storage products and software for renewables integration.",
        "gii_score": 93,
        "sustainability_update": "Deployed over 7 GW of grid-scale battery storage worldwide.",
        "esg_rating": "AA",
        "website": "https://fluenceenergy.com",
        "market_cap_fallback": 4000000000
    },
    # Indian Leaders
    "TATAPOWER.NS": {
        "name": "Tata Power Company Limited",
        "industry": "Utilities & Clean Energy",
        "description": "India's largest integrated power company driving clean energy transition with solar, wind, and EV charging infrastructure.",
        "gii_score": 91,
        "sustainability_update": "Targeting 70% clean energy portfolio by 2030 and expanding EV charging network across 500+ cities.",
        "esg_rating": "AAA",
        "website": "https://www.tatapower.com",
        "market_cap_fallback": 14000000000
    },
    "RELIANCE.NS": {
        "name": "Reliance Industries Limited",
        "industry": "Conglomerate & New Energy",
        "description": "Indian multinational conglomerate investing $10B in green hydrogen, solar gigafactories, and battery manufacturing.",
        "gii_score": 84,
        "sustainability_update": "Building Dhirubhai Ambani Green Energy Giga Complex in Jamnagar.",
        "esg_rating": "A+",
        "website": "https://www.ril.com",
        "market_cap_fallback": 240000000000
    },
    "INFY.NS": {
        "name": "Infosys Limited",
        "industry": "Information Technology",
        "description": "Global IT consulting leader and one of the first corporate entities in India to achieve carbon neutrality.",
        "gii_score": 96,
        "sustainability_update": "Maintaining 100% carbon neutrality across global campuses for the 5th consecutive year.",
        "esg_rating": "AAA",
        "website": "https://www.infosys.com",
        "market_cap_fallback": 80000000000
    },
    "TCS.NS": {
        "name": "Tata Consultancy Services",
        "industry": "Information Technology",
        "description": "Global IT services leader driving energy efficiency and digital sustainability transformations.",
        "gii_score": 92,
        "sustainability_update": "Reduced Scope 1 and Scope 2 emissions by 80% across India operations.",
        "esg_rating": "AAA",
        "website": "https://www.tcs.com",
        "market_cap_fallback": 160000000000
    },
    "ADANIGREEN.NS": {
        "name": "Adani Green Energy Limited",
        "industry": "Renewable Energy",
        "description": "One of the largest renewable energy companies in India developing massive solar and wind hybrid clusters.",
        "gii_score": 88,
        "sustainability_update": "Developing the 30 GW Khavda renewable energy park in Gujarat.",
        "esg_rating": "A",
        "website": "https://www.adanigreenenergy.com",
        "market_cap_fallback": 30000000000
    },
    "NTPC.NS": {
        "name": "NTPC Limited",
        "industry": "Utilities & Power",
        "description": "India's largest energy utility undergoing massive decarbonization by installing 60 GW of renewable capacity.",
        "gii_score": 80,
        "sustainability_update": "Commissioned India's largest floating solar PV project at Ramagundam.",
        "esg_rating": "BBB",
        "website": "https://www.ntpc.co.in",
        "market_cap_fallback": 40000000000
    },
    "SUZLON.NS": {
        "name": "Suzlon Energy Limited",
        "industry": "Wind Energy",
        "description": "India's premier wind turbine manufacturer with over 20.3 GW of cumulative wind energy capacity installed globally.",
        "gii_score": 94,
        "sustainability_update": "Launched next-gen 3.15 MW wind turbine series designed for low wind sites.",
        "esg_rating": "AA",
        "website": "https://www.suzlon.com",
        "market_cap_fallback": 8000000000
    },
    "JSWENERGY.NS": {
        "name": "JSW Energy Limited",
        "industry": "Utilities & Clean Energy",
        "description": "Leading private sector power producer pivoting rapidly to hydro, wind, and green hydrogen projects.",
        "gii_score": 86,
        "sustainability_update": "Secured 3.4 GWh battery energy storage system (BESS) contract from SECI.",
        "esg_rating": "AA",
        "website": "https://www.jsw.in/energy",
        "market_cap_fallback": 12000000000
    },
    "ITC.NS": {
        "name": "ITC Limited",
        "industry": "Consumer Goods & Paperboards",
        "description": "Diversified Indian conglomerate pioneer in carbon-positive, water-positive, and solid waste recycling operations.",
        "gii_score": 93,
        "sustainability_update": "Carbon positive for 18 consecutive years and water positive for 21 years.",
        "esg_rating": "AAA",
        "website": "https://www.itcportal.com",
        "market_cap_fallback": 65000000000
    },
    "WIPRO.NS": {
        "name": "Wipro Limited",
        "industry": "Information Technology",
        "description": "Global technology services company committed to reaching Net-Zero greenhouse gas emissions by 2040.",
        "gii_score": 91,
        "sustainability_update": "Over 55% of global electricity consumption powered by renewable sources.",
        "esg_rating": "AAA",
        "website": "https://www.wipro.com",
        "market_cap_fallback": 30000000000
    }
}


def run_finance_scraper(tickers=None):
    """
    Scrape REAL financial data - optimized for rapid polling
    
    Args:
        tickers: List of stock ticker symbols to track
    """
    print(f"💰 Fetching REAL data for tickers...")
    
    successful = 0
    failed = 0
    
    if not tickers:
        priority_tickers = list(COMPANY_METADATA.keys())
    else:
        priority_tickers = tickers
    
    for idx, ticker_symbol in enumerate(priority_tickers):
        metadata = COMPANY_METADATA.get(ticker_symbol)
        if not metadata:
            continue
        
        print(f"\n📊 [{idx+1}/{len(priority_tickers)}] {ticker_symbol}...")
        
        # Rapid polling delay between individual stocks
        if idx > 0:
            time.sleep(0.5)
        
        # Try to get real data
        price = None
        volume = 0
        change_percent = 0.0
        market_cap_value = 0
        
        for attempt in range(2):
            try:
                print(f"   🔄 Try {attempt + 1}/2...")
                ticker = yf.Ticker(ticker_symbol)
                
                # Method 1: info
                try:
                    info = ticker.info
                    if 'regularMarketPrice' in info:
                        price = float(info['regularMarketPrice'])
                        volume = int(info.get('regularMarketVolume', 0))
                        market_cap_value = info.get('marketCap', 0)
                        change_percent = float(info.get('regularMarketChangePercent', 0))
                        print(f"   ✅ ${price:.2f}")
                        break
                except:
                    pass
                
                # Method 2: history
                hist = ticker.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    volume = int(hist["Volume"].iloc[-1]) if "Volume" in hist else 0
                    if len(hist) > 1:
                        prev = float(hist["Close"].iloc[-2])
                        change_percent = ((price - prev) / prev) * 100
                    try:
                        if not info:
                            info = ticker.info
                        market_cap_value = info.get("marketCap", 0) if info else 0
                    except:
                        pass
                    print(f"   ✅ ${price:.2f}")
                    break
                    
                if attempt == 0:
                    time.sleep(10)
                    
            except Exception as e:
                print(f"   ⚠️  {str(e)[:50]}")
                if attempt == 0:
                    time.sleep(15)
        
        if price is None:
            print(f"   ❌ Failed")
            failed += 1
            continue
        
        # Use fallback market cap if API didn't provide it
        if not market_cap_value or market_cap_value == 0:
            market_cap_value = metadata.get("market_cap_fallback", 0)
        
        # Format market cap
        if market_cap_value >= 1e12:
            market_cap = f"{market_cap_value / 1e12:.1f}T"
        elif market_cap_value >= 1e9:
            market_cap = f"{market_cap_value / 1e9:.0f}B"
        else:
            market_cap = "N/A"
        
        # Save
        try:
            cur.execute(
                """
                INSERT INTO finance (
                    ticker, company_name, industry, description, gii_score,
                    stock_price, market_cap, sustainability_update, esg_rating,
                    website, price, volume, change_percent, timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    stock_price=EXCLUDED.stock_price,
                    price=EXCLUDED.price,
                    volume=EXCLUDED.volume,
                    market_cap=EXCLUDED.market_cap,
                    change_percent=EXCLUDED.change_percent,
                    timestamp=EXCLUDED.timestamp,
                    updated_at=NOW();
                """,
                (
                    ticker_symbol, metadata["name"], metadata["industry"],
                    metadata["description"], metadata["gii_score"],
                    float(price), market_cap, metadata["sustainability_update"],
                    metadata["esg_rating"], metadata["website"],
                    float(price), volume, float(change_percent), int(time.time())
                ),
            )
            conn.commit()
            successful += 1
            print(f"   ✅ Saved: ${price:.2f}, {change_percent:+.2f}%")
        except Exception as e:
            print(f"   ❌ DB: {e}")
            failed += 1
    
    print(f"\n✅ Done: {successful} OK, {failed} fail")
    return successful, failed
