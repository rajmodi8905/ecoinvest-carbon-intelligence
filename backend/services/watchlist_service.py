"""
Watchlist Service - Manages company watchlist functionality

Frontend Feature: Dashboard Center Column - Company Watchlist
Endpoints: GET /api/watchlist/companies, POST /api/watchlist/search
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for company watchlist management"""
    
    def __init__(self, pathway_reader):
        """
        Initialize Watchlist Service
        
        Args:
            pathway_reader: PathwayDataReader instance
        """
        self.pathway_reader = pathway_reader
        logger.info("✅ Watchlist Service initialized")
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """
        Get all available companies for watchlist
        
        Returns:
            List of company data with finance info
        """
        try:
            finance_data = self.pathway_reader.get_finance()
            
            # Format for watchlist display
            companies = []
            
            # The 20 priority tickers we want to show
            active_tickers = {
                'TSLA', 'MSFT', 'NVDA', 'AAPL', 'GOOGL', 'AMZN', 'ORCL', 'ENPH', 'NEE', 'FLNC',
                'TATAPOWER.NS', 'RELIANCE.NS', 'INFY.NS', 'TCS.NS', 'ADANIGREEN.NS', 'NTPC.NS', 
                'SUZLON.NS', 'JSWENERGY.NS', 'ITC.NS', 'WIPRO.NS'
            }
            
            for company in finance_data:
                ticker = company.get('ticker', '')
                if ticker not in active_tickers:
                    continue
                    
                # Use 'price' field as the source of truth, since 'stock_price' is often null
                price_value = company.get('price', 0) or company.get('stock_price', 0)
                companies.append({
                    'id': ticker,
                    'ticker': ticker,
                    'name': company.get('company_name', ''),
                    'company_name': company.get('company_name', ''),
                    'industry': company.get('industry', 'Technology'),
                    'stock_price': price_value,  # Frontend expects this field
                    'price': price_value,
                    'change_percent': company.get('change_percent', 0),
                    'market_cap': company.get('market_cap', ''),
                    'esg_rating': company.get('esg_rating', 'N/A'),
                    'gii_score': company.get('gii_score', 0),
                    'volume': company.get('volume', 0),
                    'timestamp': company.get('timestamp', 0) or company.get('time', 0),
                    'time': company.get('time', 0),
                    'description': company.get('description', ''),
                    'website': company.get('website', ''),
                    'sustainability_update': company.get('sustainability_update', '')
                })
            
            logger.info(f"📊 Retrieved {len(companies)} companies for watchlist")
            return companies
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []
    
    def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search companies by name or ticker for watchlist
        
        Args:
            query: Search query string
            
        Returns:
            List of matching companies
        """
        try:
            all_companies = self.get_all_companies()
            query_lower = query.lower()
            
            # Search by name or ticker
            results = [
                c for c in all_companies 
                if query_lower in c.get('name', '').lower() 
                or query_lower in c.get('id', '').lower()
                or query_lower in c.get('industry', '').lower()
            ]
            
            logger.info(f"🔍 Search '{query}': found {len(results)} companies")
            return results
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get specific company details by ticker
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Company data or None
        """
        try:
            finance_data = self.pathway_reader.get_finance(ticker=ticker)
            
            if finance_data and len(finance_data) > 0:
                company = finance_data[0]
                # Use 'price' field as the source of truth, since 'stock_price' is often null
                price_value = company.get('price', 0) or company.get('stock_price', 0)
                return {
                    'success': True,
                    'data': {
                        'id': company.get('ticker', ''),
                        'name': company.get('company_name', ''),
                        'industry': company.get('industry', ''),
                        'stock_price': price_value,  # Frontend expects this field
                        'price': price_value,
                        'change_percent': company.get('change_percent', 0),
                        'market_cap': company.get('market_cap', ''),
                        'esg_rating': company.get('esg_rating', 'N/A'),
                        'gii_score': company.get('gii_score', 0),
                        'description': company.get('description', ''),
                        'website': company.get('website', ''),
                        'sustainability_update': company.get('sustainability_update', '')
                    }
                }
            else:
                return {'success': False, 'error': f'Company {ticker} not found'}
        except Exception as e:
            logger.error(f"Error getting company {ticker}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_watchlist_summary(self, ticker_list: List[str]) -> Dict[str, Any]:
        """
        Get summary statistics for a list of watchlist tickers
        
        Args:
            ticker_list: List of ticker symbols
            
        Returns:
            Summary with total value, avg change, etc.
        """
        try:
            companies_data = []
            for ticker in ticker_list:
                result = self.get_company_by_ticker(ticker)
                if result.get('success'):
                    companies_data.append(result['data'])
            
            if not companies_data:
                return {'success': False, 'error': 'No valid companies in watchlist'}
            
            # Calculate summary stats
            total_value = sum(c.get('price', 0) for c in companies_data)
            avg_change = sum(c.get('change_percent', 0) for c in companies_data) / len(companies_data)
            avg_esg = sum(self._esg_to_numeric(c.get('esg_rating', 'N/A')) for c in companies_data) / len(companies_data)
            
            return {
                'success': True,
                'summary': {
                    'total_companies': len(companies_data),
                    'total_value': round(total_value, 2),
                    'avg_change_percent': round(avg_change, 2),
                    'avg_esg_score': round(avg_esg, 1),
                    'timestamp': self.pathway_reader.get_analytics().get('timestamp', '')
                }
            }
        except Exception as e:
            logger.error(f"Error getting watchlist summary: {e}")
            return {'success': False, 'error': str(e)}
    
    def _esg_to_numeric(self, rating: str) -> float:
        """Convert ESG rating to numeric value"""
        rating_map = {'AAA': 100, 'AA': 90, 'A': 80, 'BBB': 70, 'BB': 60, 'B': 50, 'CCC': 40}
        return rating_map.get(rating, 50)
