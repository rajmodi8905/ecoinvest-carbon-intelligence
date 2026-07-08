"""
Projects Service - Carbon credit projects marketplace functionality

Frontend Feature: ProjectsPage - Carbon Marketplace
Endpoints: GET /api/projects, POST /api/projects/search
"""

import logging
from typing import Dict, List, Any, Optional
from services.projects_rag_service import search_projects as rag_search_projects

logger = logging.getLogger(__name__)


class ProjectsService:
    """Service for carbon credit projects marketplace"""
    
    def __init__(self, pathway_reader):
        """
        Initialize Projects Service
        
        Args:
            pathway_reader: PathwayDataReader instance
        """
        self.pathway_reader = pathway_reader
        logger.info("✅ Projects Service initialized")
    
    def get_all_projects(self, limit: int = 500, country: str = None, category: str = None) -> Dict[str, Any]:
        """
        Get all carbon credit projects with filters
        
        Args:
            limit: Maximum number of projects
            country: Filter by country (optional)
            category: Filter by category (optional)
            
        Returns:
            Dict with projects data
        """
        try:
            projects = self.pathway_reader.get_projects(country=country, limit=limit)
            
            # Apply category filter if provided
            if category:
                projects = [p for p in projects if p.get('category') == category]
            
            # Ensure frontend compatibility - add 'id' and 'name' fields
            formatted_projects = []
            for p in projects:
                project_data = dict(p)
                project_data['id'] = p.get('project_id', '')
                project_data['name'] = p.get('project_name', '')
                formatted_projects.append(project_data)
            
            logger.info(f"🌍 Retrieved {len(formatted_projects)} projects")
            return {
                'success': True,
                'count': len(formatted_projects),
                'data': formatted_projects
            }
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return {'success': False, 'error': str(e), 'data': []}
    
    def search_projects(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Semantic search for carbon projects using RAG
        
        Args:
            query: Search query string
            limit: Maximum results
            
        Returns:
            Dict with search results
        """
        try:
            # Use RAG service for semantic search
            # Request 3x more chunks than needed because multiple chunks can belong to same project
            rag_results = rag_search_projects(query, k=min(limit * 30, 50))
            
            # If RAG service returns results, use them
            if rag_results:
                logger.info(f"🔍 RAG Search '{query}': found {len(rag_results)} chunks")
                
                # Debug: Log all chunk IDs
                for i, chunk in enumerate(rag_results):
                    chunk_id = chunk.get('id') or chunk.get('metadata', {}).get('id')
                    chunk_name = chunk.get('name') or chunk.get('metadata', {}).get('name')
                    logger.info(f"   Chunk {i+1}: ID={chunk_id}, Name={chunk_name[:50] if chunk_name else 'N/A'}...")
                
                # Extract unique project IDs from RAG chunks
                project_ids = set()
                for chunk in rag_results:
                    # Try multiple ID fields - RAG stores both 'id' and 'project_id' in metadata
                    project_id = (
                        chunk.get('id') or 
                        chunk.get('metadata', {}).get('id') or
                        chunk.get('metadata', {}).get('project_id')
                    )
                    if project_id:
                        project_ids.add(project_id)
                
                logger.info(f"📋 Extracted {len(project_ids)} unique project IDs: {list(project_ids)[:5]}...")
                
                # Get full project data specifically for the matched IDs
                all_projects = self.pathway_reader.get_projects_by_ids(list(project_ids))
                
                # Create a lookup map for fast project access
                project_map = {}
                for p in all_projects:
                    pid = p.get('project_id') or p.get('id')
                    if pid:
                        project_map[pid] = p
                        
                # Match projects strictly in the order returned by RAG (relevance)
                matched_projects = []
                seen_ids = set()
                
                for chunk in rag_results:
                    project_id = (
                        chunk.get('id') or 
                        chunk.get('metadata', {}).get('id') or
                        chunk.get('metadata', {}).get('project_id')
                    )
                    if project_id and project_id not in seen_ids and project_id in project_map:
                        seen_ids.add(project_id)
                        matched_projects.append(project_map[project_id])
                
                logger.info(f"✅ Matched {len(matched_projects)} full projects from pathway reader")
                
                # Ensure frontend compatibility
                formatted_results = []
                for p in matched_projects[:limit]:
                    project_data = dict(p)
                    project_data['id'] = p.get('project_id', '')
                    project_data['name'] = p.get('project_name', '')
                    formatted_results.append(project_data)
                
                return {
                    'success': True,
                    'query': query,
                    'count': len(formatted_results),
                    'data': formatted_results,
                    'method': 'rag'
                }
            
            # Fallback to simple text search if RAG fails
            logger.warning("⚠️ RAG search failed, falling back to simple search")
            results = self.pathway_reader.search_projects(query=query, limit=limit)
            
            # Ensure frontend compatibility
            formatted_results = []
            for p in results:
                project_data = dict(p)
                project_data['id'] = p.get('project_id', '')
                project_data['name'] = p.get('project_name', '')
                formatted_results.append(project_data)
            
            logger.info(f"🔍 Fallback Search '{query}': found {len(formatted_results)} projects")
            return {
                'success': True,
                'query': query,
                'count': len(formatted_results),
                'data': formatted_results,
                'method': 'fallback'
            }
        except Exception as e:
            logger.error(f"Error searching projects: {e}")
            return {'success': False, 'error': str(e), 'data': []}
