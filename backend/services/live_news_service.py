"""
Live News Service - Provides real-time news data for Dashboard news feed

Frontend Feature: Dashboard Right Column - Live News Feed
Endpoint: GET /api/news, WebSocket: 'news_update'
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LiveNewsService:
    """Service for live news feed functionality"""
    
    def __init__(self, pathway_reader):
        """
        Initialize Live News Service
        
        Args:
            pathway_reader: PathwayDataReader instance
        """
        self.pathway_reader = pathway_reader
        logger.info("✅ Live News Service initialized")
    
    def get_live_news(self, limit: int = 50, source: str = None) -> Dict[str, Any]:
        """
        Get live news articles for dashboard feed
        
        Args:
            limit: Maximum number of articles to return
            source: Filter by specific news source (optional)
            
        Returns:
            Dict with success status, count, and news articles
        """
        try:
            news_data = self.pathway_reader.get_news(source=source, limit=limit)
            
            # We now sort by inserted_at to ensure newly scraped items appear first,
            # falling back to published date if inserted_at is missing.
            news_data = sorted(
                news_data, 
                key=lambda x: str(x.get('inserted_at', '')) or str(x.get('published', '')), 
                reverse=True
            )
            
            # Ensure all required fields are present for frontend
            # news.jsonl has: title, summary, link, published, source, sentiment, time
            formatted_data = []
            for article in news_data:
                formatted_data.append({
                    'title': article.get('title', ''),
                    'summary': article.get('summary', ''),
                    'link': article.get('link', ''),
                    'published': article.get('published', ''),
                    'date': article.get('published', ''),  # Frontend expects 'date'
                    'source': article.get('source', ''),
                    'sentiment': article.get('sentiment', 'Neutral'),
                    'time': article.get('time', 0),
                    'news_id': article.get('news_id', None),
                    'id': article.get('news_id', None) or f"news_{article.get('time', 0)}"  # Frontend expects 'id'
                })
            
            return {
                'success': True,
                'count': len(formatted_data),
                'data': formatted_data,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting live news: {e}")
            return {'success': False, 'error': str(e), 'data': []}
    
    def get_news_by_sentiment(self, sentiment: str = "Positive", limit: int = 20) -> Dict[str, Any]:
        """
        Get news filtered by sentiment
        
        Args:
            sentiment: "Positive", "Negative", or "Neutral"
            limit: Maximum number of articles
            
        Returns:
            Dict with filtered news articles
        """
        try:
            all_news = self.pathway_reader.get_news(limit=1000)
            filtered = [n for n in all_news if n.get('sentiment') == sentiment][:limit]
            
            return {
                'success': True,
                'sentiment': sentiment,
                'count': len(filtered),
                'data': filtered
            }
        except Exception as e:
            logger.error(f"Error filtering news by sentiment: {e}")
            return {'success': False, 'error': str(e), 'data': []}
