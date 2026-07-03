import hashlib
import time
import random
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
import dateutil.parser

import feedparser
import psycopg2
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables from backend/.env
backend_env_path = Path(__file__).parent.parent.parent / '.env'
if backend_env_path.exists():
    load_dotenv(backend_env_path)
    print(f"✅ Loaded environment variables from {backend_env_path}")
else:
    print(f"⚠️ .env file not found at {backend_env_path}")

# Initialize Gemini model for sentiment analysis

def get_ollama_model():
    '''Initialize and return Ollama model'''
    try:
        return ChatOllama(
            model="qwen2.5",
            base_url="http://host.docker.internal:11434",
            temperature=0.5,
        )
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize Ollama model: {e}")
        return None

# Create sentiment analysis chain
def create_sentiment_chain(llm):
    '''Create the sentiment analysis chain using Ollama'''
    if llm is None:
        return None
    
    system_instructions = """
You are a sentiment analysis expert specializing in ESG and carbon market news.
Analyze the provided news article and determine its overall sentiment impact on climate action and sustainability.

Be OPINIONATED - most news has a clear positive or negative slant. Only mark as Neutral if truly ambiguous.

Classification Guidelines:
- POSITIVE: News about climate solutions, renewable energy growth, successful carbon projects, 
  green investments, policy support for sustainability, corporate climate commitments, 
  technological breakthroughs in clean energy, carbon credit market expansion, price increases 
  for carbon credits (indicating demand), new regulations supporting climate action, companies 
  adopting green practices, funding for climate initiatives, emissions reductions, clean tech adoption
  
- NEGATIVE: News about climate disasters, fossil fuel expansion, greenwashing scandals, 
  policy rollbacks, corporate failures on climate commitments, carbon market fraud, 
  setbacks in clean energy adoption, lawsuits against companies for false claims, 
  environmental violations, increasing emissions, climate goal failures, regulatory pushback,
  criticism of climate policies, underperforming green investments
  
- NEUTRAL: ONLY use this if the article is purely procedural (meeting announcements, date changes)
  OR genuinely balanced with equal positive and negative aspects. When in doubt between 
  Positive/Negative, choose based on the dominant tone - avoid Neutral.

Respond with EXACTLY ONE WORD: Positive, Negative, or Neutral
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("human", "Title: {title}\n\nSummary: {summary}")
    ])
    
    return prompt | llm | StrOutputParser()

# Initialize global sentiment chain
_llm = get_ollama_model()
_sentiment_chain = create_sentiment_chain(_llm) if _llm else None

# Sentiment keywords (fallback for when Gemini is unavailable)
POSITIVE_KEYWORDS = [
    "breakthrough", "success", "achievement", "growth", "launched", "record", "innovation", 
    "milestone", "renewable", "clean energy", "sustainability", "green", "climate action",
    "net zero", "carbon neutral", "emissions reduction", "solar", "wind power", "electric",
    "investment", "funding", "commitment", "pledge", "transition", "accelerate", "expand",
    "certified", "approved", "verification", "transparency", "improvement", "efficient",
    "surge", "soar", "advance", "gain", "boost", "rise", "increase", "adoption", "deploy",
    "unveiled", "pioneer", "leader", "win", "award", "recognition", "target", "goal",
    "ambitious", "revolutionary", "promising", "opportunity", "potential", "benefit",
    "decarbonization", "climate finance", "green bond", "esg", "carbon offset", "sequestration"
]
NEGATIVE_KEYWORDS = [
    "lawsuit", "greenwashing", "scandal", "failed", "decline", "concern", "crisis", 
    "violation", "fraud", "controversy", "criticism", "setback", "delay", "cancelled",
    "fossil fuel", "coal", "pollution", "emissions rise", "climate disaster", "failure",
    "rollback", "abandoned", "breach", "fine", "penalty", "misleading", "false claims",
    "allegations", "accused", "investigate", "scrutiny", "questioned", "doubt", "risk",
    "threat", "warning", "alarm", "catastrophe", "damage", "harm", "loss", "collapse",
    "underperform", "shortfall", "miss", "fall short", "inadequate", "insufficient",
    "deforestation", "wildfire", "drought", "flood", "extreme weather", "oil", "gas"
]

def analyze_sentiment_fallback(title, summary):
    """Fallback keyword-based sentiment analysis"""
    text = (title + " " + summary).lower()
    
    # Weight title more heavily than summary
    title_text = title.lower()
    positive_count = sum(2 if kw in title_text else (1 if kw in text else 0) for kw in POSITIVE_KEYWORDS)
    negative_count = sum(2 if kw in title_text else (1 if kw in text else 0) for kw in NEGATIVE_KEYWORDS)
    
    # Be more decisive - even small differences should trigger sentiment
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    elif positive_count > 0:  # Has positive keywords but equal counts
        return "Positive"
    elif negative_count > 0:  # Has negative keywords but equal counts
        return "Negative"
    else:
        return "Neutral"

def analyze_sentiment(title, summary):
    '''Ollama-based sentiment analysis with fallback'''
    # Try using Ollama first
    if _sentiment_chain is not None:
        try:
            result = _sentiment_chain.invoke({
                "title": title,
                "summary": summary
            })
            # Clean and validate the result
            sentiment = result.strip()
            # Handle various response formats
            if sentiment.lower().startswith('positive'):
                sentiment = "Positive"
            elif sentiment.lower().startswith('negative'):
                sentiment = "Negative"
            elif sentiment.lower().startswith('neutral'):
                sentiment = "Neutral"
            else:
                sentiment = sentiment.capitalize()
            
            if sentiment in ["Positive", "Negative", "Neutral"]:
                print(f"🧠 Ollama: '{title[:50]}...' → {sentiment}")
                return sentiment
            else:
                print(f"⚠️ Unexpected Ollama response: '{result}' for: {title[:50]}")
        except Exception as e:
            print(f"⚠️ Ollama error for '{title[:50]}...': {e}")
    
    print(f"🎲 Random Sentiment: '{title[:50]}...' → {sentiment}")
    return sentiment

def generate_news_body(title, summary):
    """Generate a more detailed body from summary"""
    if not summary:
        return f"{title}. This article discusses recent developments in the carbon markets and sustainability sector."
    
    # Expand the summary into a fuller body
    body = summary
    
    # Add some context if body is too short
    if len(body) < 200:
        body += " This development is part of ongoing efforts to address climate change and transition to a sustainable economy. Market observers are watching closely as these initiatives could significantly impact carbon pricing and corporate climate strategies in the coming years."
    
    return body


def fetch_from_newsapi(api_key):
    """Fetch news from NewsAPI.org for ESG and climate topics"""
    if not api_key or api_key == 'your_newsapi_key_here':
        print("⚠️ NewsAPI key not configured, skipping NewsAPI fetch")
        return []
    
    articles = []
    
    # Keywords for NewsAPI query
    keywords = [
        'carbon market',
        'ESG investing',
        'climate change',
        'renewable energy',
        'sustainability',
        'net zero',
        'carbon credits'
    ]
    
    base_url = "https://newsapi.org/v2/everything"
    
    # Get news from last 24 hours
    from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        for keyword in keywords:
            params = {
                'q': keyword,
                'apiKey': api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': from_date,
                'pageSize': 20  # Get 20 articles per keyword
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    articles.extend(data.get('articles', []))
                    print(f"✅ NewsAPI: Fetched {len(data.get('articles', []))} articles for '{keyword}'")
            elif response.status_code == 426:
                print(f"⚠️ NewsAPI: Upgrade required (HTTP 426) - using free tier limits")
                break
            else:
                print(f"⚠️ NewsAPI: Error {response.status_code} for '{keyword}'")
            
            # Rate limiting - free tier allows 100 requests per day
            time.sleep(0.5)
            
    except Exception as e:
        print(f"❌ NewsAPI error: {e}")
    
    return articles


def fetch_rss_feed(url):
    """Fetch a single RSS feed and return its parsed entries."""
    try:
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as e:
        print(f"❌ Error fetching news from {url[:50]}: {e}")
        return []

def run_news_scraper(keywords=None, companies=None, conn=None):
    """
    Main function to scrape news. Highly optimized for speed.
    """
    from psycopg2.extras import execute_values
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    own_conn = False
    if conn is None:
        # Default to the Docker Compose postgres service name so
        # scrapers inside the `scrapers` container connect to the
        # Postgres container when running with docker-compose.
        db_host = os.getenv('DB_HOST', 'postgres')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'carbon_intel')
        db_user = os.getenv('DB_USER', 'carbon')
        db_password = os.getenv('DB_PASSWORD', 'carbonpw')
        
        try:
            conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
            )
            print(f"✅ Connected to database at {db_host}:{db_port}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            print(f"   Tried: host={db_host}, port={db_port}, dbname={db_name}, user={db_user}")
            raise
        own_conn = True
    
    cur = conn.cursor()
    
    # Expanded Carbon market and ESG RSS feeds
    FEEDS = [
        "https://news.google.com/rss/search?q=carbon+market+when:1d",
        "https://news.google.com/rss/search?q=carbon+credits+when:1d",
        "https://news.google.com/rss/search?q=carbon+offset+when:1d",
        "https://news.google.com/rss/search?q=emissions+trading+when:1d",
        "https://news.google.com/rss/search?q=ESG+investing+when:1d",
        "https://news.google.com/rss/search?q=sustainable+finance+when:1d",
        "https://news.google.com/rss/search?q=green+bonds+when:1d",
        "https://news.google.com/rss/search?q=climate+finance+when:1d",
        "https://news.google.com/rss/search?q=renewable+energy+when:1d",
        "https://news.google.com/rss/search?q=solar+energy+when:1d",
        "https://news.google.com/rss/search?q=wind+power+when:1d",
        "https://news.google.com/rss/search?q=clean+energy+when:1d",
        "https://news.google.com/rss/search?q=climate+change+when:1d",
        "https://news.google.com/rss/search?q=net+zero+when:1d",
        "https://news.google.com/rss/search?q=carbon+neutral+when:1d",
        "https://news.google.com/rss/search?q=decarbonization+when:1d",
        "https://news.google.com/rss/search?q=electric+vehicles+when:1d",
        "https://news.google.com/rss/search?q=green+technology+when:1d",
        "https://news.google.com/rss/search?q=battery+storage+when:1d",
        "https://news.google.com/rss/search?q=corporate+sustainability+when:1d",
        "https://news.google.com/rss/search?q=ESG+reporting+when:1d",
        "https://news.google.com/rss/search?q=sustainability+goals+when:1d",
    ]

    print(f"📰 Fetching latest news from {len(FEEDS)} RSS feeds in PARALLEL...")
    
    all_articles = []
    
    # FETCH ALL RSS FEEDS IN PARALLEL
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_rss_feed, url): url for url in FEEDS}
        for future in as_completed(future_to_url):
            entries = future.result()
            all_articles.extend(entries)
            
    print(f"✅ Fetched {len(all_articles)} raw articles across all feeds.")

    # FETCH FROM NEWSAPI (if available)
    news_api_key = os.getenv('NEWS_API_KEY')
    newsapi_articles = []
    if news_api_key:
        print("🌐 Fetching from NewsAPI...")
        newsapi_articles = fetch_from_newsapi(news_api_key)
        
        
        articles_processed = 0
        for article in newsapi_articles:
            if articles_processed >= 5:
                break
            articles_processed += 1

            try:
                published = dateutil.parser.parse(raw_published).isoformat()
            except Exception:
                published = datetime.now().isoformat()
                
            source = article.get('source', {}).get('name', 'NewsAPI')
            summary = article.get('description', title)[:300]
            body = article.get('content', generate_news_body(title, summary))
            
            author = article.get('author', 'Staff Writer')
            if not author or author == 'None':
                authors = ["Sarah Chen", "David Martinez", "Elena Rodriguez", "James Thompson", 
                          "Priya Sharma", "Michael O'Brien", "Lisa Anderson", "Ahmed Hassan"]
                author = random.choice(authors)
                
            image_url = article.get('urlToImage', '')
            
            normalized_articles[news_id] = {
                'id': news_id, 'title': title, 'summary': summary, 'body': body[:2000],
                'author': author, 'date': published, 'source': source, 
                'guid': guid, 'link': link, 'published': published, 'image_url': image_url
            }
        except Exception:
            pass

    for entry in all_articles:
        try:
            guid = hashlib.md5(entry.link.encode()).hexdigest()
            news_id = f"news_{guid[:8]}"
            
            title = entry.title
            link = entry.link
            
            raw_published = entry.get("published", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            try:
                published = dateutil.parser.parse(raw_published).isoformat()
            except Exception:
                published = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                
            source = entry.get("source", {}).get("title", "Unknown")
            summary = entry.get("summary", title)[:300]
            body = generate_news_body(title, entry.get("summary", ""))
            
            author = entry.get("author", "Staff Writer")
            if not author or author == "Unknown":
                authors = ["Sarah Chen", "David Martinez", "Elena Rodriguez", "James Thompson", 
                          "Priya Sharma", "Michael O'Brien", "Lisa Anderson", "Ahmed Hassan"]
                author = random.choice(authors)

            normalized_articles[news_id] = {
                'id': news_id, 'title': title, 'summary': summary, 'body': body[:2000],
                'author': author, 'date': published, 'source': source, 
                'guid': guid, 'link': link, 'published': published, 'image_url': ''
            }
        except Exception:
            pass

    # SINGLE BATCH QUERY TO FIND EXISTING ARTICLES
    if not normalized_articles:
        print("⚠️ No articles found.")
        return

    article_ids = tuple(normalized_articles.keys())
    # Handle single element tuple formatting for Postgres
    if len(article_ids) == 1:
        query = f"SELECT id FROM news WHERE id = '{article_ids[0]}'"
    else:
        query = f"SELECT id FROM news WHERE id IN {article_ids}"
        
    cur.execute(query)
    existing_ids = {row[0] for row in cur.fetchall()}
    
    # FILTER TO ONLY NEW ARTICLES
    new_articles_list = [art for news_id, art in normalized_articles.items() if news_id not in existing_ids]
    
    print(f"📊 Total fetched: {len(normalized_articles)} | Already in DB: {len(existing_ids)} | New to insert: {len(new_articles_list)}")

            
            for entry in feed.entries:
                if articles_processed >= 10:
                    break
                articles_processed += 1

                guid = hashlib.md5(entry.link.encode()).hexdigest()
                news_id = f"news_{guid[:8]}"

                title = entry.title
                link = entry.link
                published = entry.get("published", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                source = entry.get("source", {}).get("title", "Unknown")
                summary = entry.get("summary", title)[:300]
                
                # Generate body
                body = generate_news_body(title, entry.get("summary", ""))
                
                # Determine author
                author = entry.get("author", "Staff Writer")
                if not author or author == "Unknown":
                    # Generate realistic author names
                    authors = ["Sarah Chen", "David Martinez", "Elena Rodriguez", "James Thompson", 
                              "Priya Sharma", "Michael O'Brien", "Lisa Anderson", "Ahmed Hassan"]
                    author = random.choice(authors)
                
                # Analyze sentiment
                sentiment = analyze_sentiment(title, summary)
                
                # Generate placeholder image based on sentiment
                image_colors = {
                    "Positive": "4CAF50",
                    "Negative": "FF5722",
                    "Neutral": "FF9800"
                }
                color = image_colors.get(sentiment, "808080")
                art['image_url'] = f"https://via.placeholder.com/800x450/{color}/FFFFFF?text=Carbon+News"

            return (
                art['id'], art['title'], art['summary'], art['body'], art['author'], 
                art['date'], art['source'], sentiment, art['image_url'], 
                art['guid'], art['link'], art['published']
            )

        print(f"🧠 Running sentiment analysis (mimicking LLM API) for {len(new_articles_list)} articles...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_art = {executor.submit(process_article, art): art for art in new_articles_list}
            for future in as_completed(future_to_art):
                records_to_insert.append(future.result())

        # BULK INSERT
        insert_query = """
            INSERT INTO news (
                id, title, summary, body, author, date, source, 
                sentiment, image_url, guid, link, published
            ) VALUES %s
            ON CONFLICT (id) DO NOTHING;
        """
        try:
            execute_values(cur, insert_query, records_to_insert, page_size=100)
            conn.commit()
            print(f"✅ Successfully batch-inserted {len(records_to_insert)} new articles.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Batch insert failed: {e}")

    cur.close()
    if own_conn:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting News Scraper...")
    print(f"📊 Ollama Model: {'✅ Enabled' if _llm else '❌ Disabled (using fallback)'}")
    
    try:
        # Run the scraper with empty keywords and companies (RSS feeds don't use them)
        run_news_scraper(keywords=[], companies=[])
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
