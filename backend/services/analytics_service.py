"""
Analytics Service - Dashboard analytics and metrics

Frontend Feature: Dashboard - Analytics Overview
Endpoints: GET /api/analytics, GET /api/analytics/esg, GET /api/analytics/carbon-trends,
           GET /api/analytics/macro-themes, GET /api/analytics/credit-index,
           GET /api/analytics/top-movers
"""

import re
import math
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for dashboard analytics and metrics"""
    
    def __init__(self, pathway_reader):
        """
        Initialize Analytics Service
        
        Args:
            pathway_reader: PathwayDataReader instance
        """
        self.pathway_reader = pathway_reader
        logger.info("✅ Analytics Service initialized")
    
    def get_dashboard_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics for dashboard overview
        
        Returns:
            Dict with all analytics metrics
        """
        try:
            analytics = self.pathway_reader.get_analytics()
            
            return {
                'success': True,
                'analytics': analytics.get('analytics', {}),
                'projects': analytics.get('projects', {}),
                'finance': analytics.get('finance', {}),
                'news': analytics.get('news', {}),
                'timestamp': analytics.get('timestamp', '')
            }
        except Exception as e:
            logger.error(f"Error getting dashboard analytics: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_esg_analysis(self, tickers: List[str] = None) -> Dict[str, Any]:
        """
        Analyze ESG scores across companies
        
        Args:
            tickers: Optional list of specific tickers to analyze
            
        Returns:
            Dict with ESG analysis results
        """
        try:
            if tickers:
                finance_data = []
                for ticker in tickers:
                    data = self.pathway_reader.get_finance(ticker=ticker)
                    finance_data.extend(data)
            else:
                finance_data = self.pathway_reader.get_finance()
            
            if not finance_data:
                return {'success': False, 'error': 'No finance data available'}
            
            # Calculate ESG metrics
            esg_scores = defaultdict(list)
            for company in finance_data:
                rating = company.get('esg_rating', 'N/A')
                gii_score = company.get('gii_score', 0)
                if rating != 'N/A' and gii_score > 0:
                    esg_scores[rating].append(gii_score)
            
            # Average GII score per ESG rating
            esg_summary = {}
            for rating, scores in esg_scores.items():
                esg_summary[rating] = {
                    'avg_gii_score': round(sum(scores) / len(scores), 2),
                    'company_count': len(scores)
                }
            
            return {
                'success': True,
                'total_companies': len(finance_data),
                'esg_distribution': esg_summary,
                'avg_gii_score': round(sum(c.get('gii_score', 0) for c in finance_data) / len(finance_data), 2)
            }
        except Exception as e:
            logger.error(f"Error analyzing ESG scores: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_carbon_trends(self) -> Dict[str, Any]:
        """
        Analyze carbon credit market trends
        
        Returns:
            Dict with carbon market trends
        """
        try:
            projects = self.pathway_reader.get_projects(limit=10000)
            
            if not projects:
                return {'success': False, 'error': 'No projects data available'}
            
            # Price trends by category
            category_stats = defaultdict(lambda: {'total_credits': 0, 'total_value': 0, 'count': 0, 'prices': []})
            
            for project in projects:
                cat = project.get('category', 'Other')
                credits = project.get('available_credits', 0)
                price = project.get('price', 0)
                
                category_stats[cat]['total_credits'] += credits
                category_stats[cat]['total_value'] += credits * price
                category_stats[cat]['count'] += 1
                category_stats[cat]['prices'].append(price)
            
            # Calculate averages
            trends = {}
            for cat, stats in category_stats.items():
                avg_price = sum(stats['prices']) / len(stats['prices']) if stats['prices'] else 0
                trends[cat] = {
                    'total_credits': stats['total_credits'],
                    'total_value': round(stats['total_value'], 2),
                    'project_count': stats['count'],
                    'avg_price': round(avg_price, 2)
                }
            
            return {
                'success': True,
                'total_supply': sum(p.get('available_credits', 0) for p in projects),
                'avg_price': round(sum(p.get('price', 0) for p in projects) / len(projects), 2),
                'category_trends': trends
            }
        except Exception as e:
            logger.error(f"Error analyzing carbon trends: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_news_sentiment_analysis(self) -> Dict[str, Any]:
        """
        Analyze sentiment distribution in news
        
        Returns:
            Dict with sentiment analysis
        """
        try:
            news = self.pathway_reader.get_news(limit=1000)
            
            if not news:
                return {'success': False, 'error': 'No news data available'}
            
            # Count sentiments
            sentiment_counts = defaultdict(int)
            for article in news:
                sentiment = article.get('sentiment', 'Neutral')
                sentiment_counts[sentiment] += 1
            
            total = len(news)
            sentiment_distribution = {
                sentiment: {
                    'count': count,
                    'percentage': round((count / total) * 100, 1)
                }
                for sentiment, count in sentiment_counts.items()
            }
            
            return {
                'success': True,
                'total_articles': total,
                'sentiment_distribution': sentiment_distribution,
                'dominant_sentiment': max(sentiment_counts.items(), key=lambda x: x[1])[0]
            }
        except Exception as e:
            logger.error(f"Error analyzing news sentiment: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_market_summary(self) -> Dict[str, Any]:
        """
        Get overall market summary statistics
        
        Returns:
            Dict with market summary
        """
        try:
            projects = self.pathway_reader.get_projects(limit=10000)
            finance = self.pathway_reader.get_finance()
            news = self.pathway_reader.get_news(limit=100)
            
            # Calculate key metrics
            total_carbon_supply = sum(p.get('available_credits', 0) for p in projects)
            avg_carbon_price = sum(p.get('price', 0) for p in projects) / len(projects) if projects else 0
            
            # Stock market performance
            avg_stock_change = sum(c.get('change_percent', 0) for c in finance) / len(finance) if finance else 0
            
            # Recent news sentiment
            recent_positive = sum(1 for n in news[:20] if n.get('sentiment') == 'Positive')
            sentiment_score = (recent_positive / 20) * 100 if len(news) >= 20 else 50
            
            return {
                'success': True,
                'market_summary': {
                    'carbon_market': {
                        'total_supply': total_carbon_supply,
                        'avg_price': round(avg_carbon_price, 2),
                        'active_projects': len(projects)
                    },
                    'stock_market': {
                        'tracked_companies': len(finance),
                        'avg_change_percent': round(avg_stock_change, 2)
                    },
                    'sentiment_score': round(sentiment_score, 1),
                    'recent_news_count': len(news)
                }
            }
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {'success': False, 'error': str(e)}

    # ────────────────────────────────────────────────────────────────────────────
    # NEW: Macro Themes — groups news by climate/policy narrative
    # ────────────────────────────────────────────────────────────────────────────

    # Keyword → theme mapping (order matters: first match wins)
    THEME_KEYWORDS = {
        "Renewable Energy":  ["solar", "wind", "renewable", "clean energy", "photovoltaic", "hydrogen", "geothermal"],
        "Carbon Markets":    ["carbon credit", "carbon market", "offset", "verra", "carbonmark", "cap-and-trade", "emissions trading"],
        "Regulation":        ["regulation", "policy", "legislation", "carbon tax", "emissions limit", "cop", "climate law"],
        "Banking & Finance": ["bank", "finance", "investment", "fund", "esg investing", "bond", "asset manager"],
        "Climate":           ["climate", "global warming", "net zero", "temperature", "ipcc", "paris agreement"],
        "Geopolitics":       ["geopolit", "sanction", "trade war", "tariff", "diplomacy", "nato", "geopolitics"],
        "Tech Sector":       ["technology", "artificial intelligence", " ai ", "data center", "semiconductor", "chip"],
        "Inflation":         ["inflation", "cpi", "interest rate", "federal reserve", "monetary policy", "fed "],
        "Energy":            ["oil", " gas ", "lng", "energy crisis", "power grid", "nuclear", "fossil"],
        "Agriculture":       ["agriculture", "farming", "deforestation", "redd", "land use", "forest"],
    }

    def _classify_article(self, title: str, summary: str) -> str:
        """Return the best-matching macro theme for an article."""
        text = (title + " " + summary).lower()
        for theme, keywords in self.THEME_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return theme
        return "General"

    def _sentiment_to_num(self, s: str) -> float:
        return {"Positive": 1.0, "Negative": -1.0}.get(s, 0.0)

    def get_macro_themes(self) -> Dict[str, Any]:
        """
        Group news by macro theme, compute velocity + confidence + rolling sentiment.

        velocity   = 1 − 2^(−ratio), ratio = (24·N1h / N24h) · min(1, N24h / 10)  [clamped 0..1]
        confidence = 0.4·min(1,N24h/20) + 0.3·min(1,sources/5) + 0.3·|mean_sign|
        """
        try:
            news = self.pathway_reader.get_news(limit=2000)
            if not news:
                return {'success': True, 'themes': []}

            now = datetime.now(timezone.utc)

            # Bucket articles into themes
            buckets: Dict[str, List[Dict]] = defaultdict(list)
            for article in news:
                theme = self._classify_article(
                    article.get('title', ''),
                    article.get('summary', '')
                )
                buckets[theme].append(article)

            # Parse publish timestamp (ISO string or epoch int)
            def parse_ts(article):
                pub = article.get('published') or article.get('date') or ''
                t = article.get('time') or article.get('timestamp') or 0
                if pub:
                    try:
                        dt = datetime.fromisoformat(pub.replace('Z', '+00:00'))
                        return dt.timestamp()
                    except Exception:
                        pass
                return float(t) / 1000.0 if t > 1e10 else float(t)

            themes_out = []
            for theme, articles in buckets.items():
                ts_list = [parse_ts(a) for a in articles]
                now_ts = now.timestamp()

                n_24h = sum(1 for t in ts_list if (now_ts - t) <= 86400)
                n_1h  = sum(1 for t in ts_list if (now_ts - t) <= 3600)
                sources = set(a.get('source', '') for a in articles if a.get('source'))
                n_sources = len(sources)

                sentiments = [self._sentiment_to_num(a.get('sentiment', 'Neutral')) for a in articles]
                mean_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0

                # Transition Momentum (theme sentiment direction * recent volume)
                vol_ratio = n_1h / max(1, n_24h)
                momentum = mean_sent * (1.0 + vol_ratio)
                
                # Impact Score (normalized 0-100)
                impact = min(100, (n_24h * 2) + (abs(mean_sent) * 20))

                # Latest headline
                sorted_arts = sorted(articles, key=lambda a: parse_ts(a), reverse=True)
                latest_headline = sorted_arts[0].get('title', '') if sorted_arts else ''

                themes_out.append({
                    'theme': theme,
                    'articles_24h': n_24h,
                    'articles_1h': n_1h,
                    'unique_sources': n_sources,
                    'sentiment': round(mean_sent, 3),
                    'momentum': round(momentum, 3),
                    'impact': round(impact, 1),
                    'latest_headline': latest_headline,
                    'total_articles': len(articles),
                })

            themes_out.sort(key=lambda x: x['articles_24h'], reverse=True)

            # Overall KPIs
            total_24h = sum(t['articles_24h'] for t in themes_out)
            avg_sent = (sum(t['sentiment'] for t in themes_out) / len(themes_out)) if themes_out else 0
            hottest = max(themes_out, key=lambda x: x['impact'], default={}).get('theme', '')

            return {
                'success': True,
                'themes': themes_out,
                'total_themes': len(themes_out),
                'total_articles_24h': total_24h,
                'avg_sentiment': round(avg_sent, 3),
                'hottest_theme': hottest,
            }
        except Exception as e:
            logger.error(f"Error computing macro themes: {e}")
            return {'success': False, 'error': str(e)}

    # ────────────────────────────────────────────────────────────────────────────
    # NEW: Credit Index — category-level VCM benchmark
    # ────────────────────────────────────────────────────────────────────────────

    def get_credit_index(self) -> Dict[str, Any]:
        """
        Build the Carbon Credit Index: category-level aggregation of Verra projects
        enriched with Carbonmark best-ask prices.
        """
        try:
            projects = self.pathway_reader.get_projects(limit=10000)
            if not projects:
                return {'success': False, 'error': 'No projects data'}

            cat_stats = defaultdict(lambda: {
                'prices': [], 'supply': 0, 'market_value': 0,
                'project_count': 0, 'listing_count': 0,
            })

            for p in projects:
                cat = p.get('category') or 'Other'
                price = float(p.get('price') or 0)
                credits = int(p.get('available_credits') or 0)
                # carbonmark 'amount' field = listing best-ask
                amount = float(p.get('amount') or 0)
                has_listing = amount > 0

                cat_stats[cat]['project_count'] += 1
                cat_stats[cat]['supply'] += credits
                if has_listing:
                    cat_stats[cat]['listing_count'] += 1
                if price > 0:
                    cat_stats[cat]['prices'].append(price)
                    cat_stats[cat]['market_value'] += price * credits

            index = []
            global_floor = None

            for cat, s in cat_stats.items():
                prices = s['prices']
                floor = min(prices) if prices else 0
                avg   = sum(prices) / len(prices) if prices else 0
                mx    = max(prices) if prices else 0

                if floor > 0 and (global_floor is None or floor < global_floor):
                    global_floor = floor

                index.append({
                    'category':      cat,
                    'floor':         round(floor, 4),
                    'avg':           round(avg, 4),
                    'max':           round(mx, 4),
                    'supply':        s['supply'],
                    'market_value':  round(s['market_value'], 2),
                    'project_count': s['project_count'],
                    'listing_count': s['listing_count'],
                })

            index.sort(key=lambda x: x['market_value'], reverse=True)

            total_mkt_val  = sum(i['market_value'] for i in index)
            traded_projects = sum(i['listing_count'] for i in index)

            return {
                'success': True,
                'index': index,
                'market_floor': round(global_floor, 4) if global_floor else 0,
                'total_market_value': round(total_mkt_val, 2),
                'traded_projects': traded_projects,
                'total_categories': len(index),
            }
        except Exception as e:
            logger.error(f"Error computing credit index: {e}")
            return {'success': False, 'error': str(e)}

    # ────────────────────────────────────────────────────────────────────────────
    # NEW: Top Movers — companies enriched with live news signals
    # ────────────────────────────────────────────────────────────────────────────

    def get_top_movers(self) -> Dict[str, Any]:
        """
        Enrich all companies with news-derived live signals:
          risk, velocity, confidence, sentiment_24h, news_count_24h, unique_sources.

        Ticker matching uses word-boundary regex to avoid false positives.
        """
        try:
            finance = self.pathway_reader.get_finance()
            news    = self.pathway_reader.get_news(limit=2000)

            if not finance:
                return {'success': False, 'error': 'No finance data'}

            # Pre-compile regex patterns per ticker + company name
            patterns = {}
            for c in finance:
                ticker = c.get('ticker', '').strip()
                name   = c.get('company_name', '').strip()
                parts  = [re.escape(ticker)] if ticker else []
                if name and len(name) > 3:
                    parts.append(re.escape(name))
                if parts:
                    patterns[ticker] = re.compile(
                        r'\b(' + '|'.join(parts) + r')\b', re.IGNORECASE
                    )

            now_ts = datetime.now(timezone.utc).timestamp()

            def ts_of(article):
                t = article.get('time') or article.get('timestamp') or 0
                pub = article.get('published') or ''
                if pub:
                    try:
                        return datetime.fromisoformat(pub.replace('Z', '+00:00')).timestamp()
                    except Exception:
                        pass
                return float(t) / 1000.0 if t > 1e10 else float(t)

            results = []
            for c in finance:
                ticker = c.get('ticker', '')
                pat = patterns.get(ticker)

                matched = []
                if pat:
                    for a in news:
                        text = (a.get('title', '') + ' ' + a.get('summary', ''))
                        if pat.search(text):
                            matched.append(a)

                ts_list  = [ts_of(a) for a in matched]
                n_24h    = sum(1 for t in ts_list if (now_ts - t) <= 86400)
                n_1h     = sum(1 for t in ts_list if (now_ts - t) <= 3600)
                sources  = set(a.get('source', '') for a in matched if a.get('source'))
                n_src    = len(sources)

                sents    = [self._sentiment_to_num(a.get('sentiment', 'Neutral')) for a in matched]
                mean_s   = sum(sents) / len(sents) if sents else 0.0

                # ESG Multiplier
                esg_rating = c.get('esg_rating', 'N/A')
                esg_map = {'AAA': 100, 'AA': 90, 'A': 80, 'BBB': 70, 'BB': 60, 'B': 50, 'CCC': 40}
                esg_score = esg_map.get(esg_rating, 60)
                
                # Carbon Impact Rating (CIR)
                gii = c.get('gii_score', 0)
                impact_rating = (esg_score * 0.7) + (gii * 0.3)
                
                # Policy Alignment
                industry = c.get('industry', '')
                ind_base = 50
                if 'Renewable' in industry or 'Clean' in industry:
                    ind_base = 85
                elif 'Tech' in industry:
                    ind_base = 65
                elif 'Oil' in industry or 'Gas' in industry or 'Fossil' in industry:
                    ind_base = 20
                policy_alignment = min(100, max(0, ind_base + (mean_s * 15)))
                
                # Transition Momentum
                chg = float(c.get('change_percent') or 0)
                chg_norm = max(-1.0, min(1.0, chg / 5.0)) # cap at +/- 5%
                momentum = (mean_s * 0.6) + (chg_norm * 0.4)
                
                # Composite risk (simplified)
                s_norm = (mean_s + 1) / 2  # map [-1,1] → [0,1]
                p_neg  = max(0.0, -chg / 100.0)
                risk   = ((1 - s_norm) * (1 + 0.5 * p_neg)) / 2.0

                price_val = float(c.get('price') or c.get('stock_price') or 0)

                results.append({
                    'ticker':         ticker,
                    'company_name':   c.get('company_name', ''),
                    'industry':       c.get('industry', ''),
                    'price':          round(price_val, 2),
                    'change_percent': round(chg, 2),
                    'market_cap':     c.get('market_cap', ''),
                    'esg_rating':     c.get('esg_rating', 'N/A'),
                    'gii_score':      c.get('gii_score', 0),
                    'risk':             round(risk, 3),
                    'impact_rating':    round(impact_rating, 1),
                    'policy_alignment': round(policy_alignment, 1),
                    'momentum':         round(momentum, 3),
                    'sentiment_24h':    round(mean_s, 3),
                    'news_24h':         n_24h,
                })

            results.sort(key=lambda x: x['risk'], reverse=True)

            return {
                'success': True,
                'companies': results,
                'total': len(results),
            }
        except Exception as e:
            logger.error(f"Error computing top movers: {e}")
            return {'success': False, 'error': str(e)}

