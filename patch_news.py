import re

with open("backend/carbon-intelligence/scrapers/news_scraper.py", "r") as f:
    content = f.read()

# Replace Gemini imports with Ollama
content = content.replace("from langchain_google_genai import ChatGoogleGenerativeAI", "from langchain_ollama import ChatOllama")

# Replace get_gemini_model with get_ollama_model
ollama_model_code = """
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
"""
# Use regex to replace the get_gemini_model function
content = re.sub(r'def get_gemini_model\(\):.*?(?=\n# Create sentiment analysis chain)', ollama_model_code, content, flags=re.DOTALL)

# Update sentiment chain definition
content = content.replace("def create_sentiment_chain(llm):", "def create_sentiment_chain(llm):\n    '''Create the sentiment analysis chain using Ollama'''")
content = re.sub(r'\"\"\"Create the sentiment analysis chain using Gemini\"\"\"\n', '', content)

# Update global initialization
content = content.replace("_llm = get_gemini_model()", "_llm = get_ollama_model()")

# Update analyze_sentiment function
content = content.replace("def analyze_sentiment(title, summary):\n    \"\"\"Gemini-based sentiment analysis with fallback\"\"\"\n    # Try using Gemini first", "def analyze_sentiment(title, summary):\n    '''Ollama-based sentiment analysis with fallback'''\n    # Try using Ollama first")
content = content.replace("Gemini:", "Ollama:")
content = content.replace("Gemini error", "Ollama error")
content = content.replace("Unexpected Gemini response:", "Unexpected Ollama response:")

# Limit articles in run_news_scraper
# Find the start of NewsAPI processing
newsapi_start = "for article in newsapi_articles:"
newsapi_limit = """
        articles_processed = 0
        for article in newsapi_articles:
            if articles_processed >= 5:
                break
            articles_processed += 1
"""
content = content.replace(newsapi_start, newsapi_limit)

# Find the start of RSS processing
rss_start = "for entry in feed.entries:"
rss_limit = """
            for entry in feed.entries:
                if articles_processed >= 10:
                    break
                articles_processed += 1
"""
content = content.replace(rss_start, rss_limit)

# Replace final print
content = content.replace("📊 Gemini Model:", "📊 Ollama Model:")

with open("backend/carbon-intelligence/scrapers/news_scraper.py", "w") as f:
    f.write(content)

print("Patch applied!")
