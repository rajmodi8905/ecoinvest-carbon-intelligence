"""
Project Report Service - AI-powered project details and reports

Three main functions for project report page:
1. get_project_details() - Basic project information
2. generate_project_report() - AI-generated comprehensive report  
3. custom_query() - Answer custom questions about the project
"""

import logging
from typing import Dict, Any, Optional
from llm_manager import get_llm
import markdown

# Try to import LangChain components for agent-based custom_query
try:
    from langgraph.prebuilt import create_react_agent

    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.memory import MemorySaver
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class ProjectReportService:
    """Service for project report page with 3 sections"""
    
    def __init__(self, pathway_reader):
        """
        Initialize Project Report Service
        
        Args:
            pathway_reader: PathwayDataReader instance
        """
        self.pathway_reader = pathway_reader
        logger.info("✅ Project Report Service initialized")
    
    def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """
        Section 1: Get basic project details
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict with project details
        """
        try:
            # Get project data from Pathway
            project_result = self.pathway_reader.get_projects(limit=10000)
            project = next(
                (p for p in project_result if p.get('project_id') == project_id), 
                None
            )
            
            if not project:
                return {
                    'success': False, 
                    'error': f'Project {project_id} not found'
                }
            
            return {
                'success': True,
                'data': {
                    'id': project.get('project_id', ''),
                    'project_id': project.get('project_id', ''),
                    'name': project.get('project_name', ''),
                    'project_name': project.get('project_name', ''),
                    'country': project.get('country', 'N/A'),
                    'category': project.get('category', 'N/A'),
                    'methodology': project.get('methodology', 'N/A'),
                    'vintage': project.get('vintage', 'N/A'),
                    'available_credits': project.get('available_credits', 0),
                    'price': project.get('price', 0),
                    'registry_status': project.get('registry_status', 'N/A'),
                    'description': project.get('description', 'No description available'),
                    'image_url': project.get('image_url', ''),
                    'registry_url': project.get('registry_url', ''),
                    'total_supply': project.get('total_supply', 0),
                    'retired': project.get('retired', 0),
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting project details for {project_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_project_report(self, project_id: str) -> Dict[str, Any]:
        """
        Section 2: Generate AI-powered comprehensive report
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict with AI-generated report
        """
        try:
            # Get project details first
            project_result = self.get_project_details(project_id)
            if not project_result.get('success'):
                return project_result
            
            project = project_result['data']
            
            # Generate AI-powered report using centralized LLM
            ai_report = None
            llm = get_llm()
            
            if llm:
                try:
                    logger.info(f"🤖 Generating AI report for {project_id}...")
                    prompt = self._create_report_prompt(project)
                    response = llm.invoke(prompt)
                    ai_report_markdown = response.content
                    # Convert markdown to HTML for proper formatting
                    ai_report = markdown.markdown(ai_report_markdown, extensions=['nl2br', 'sane_lists'])
                    logger.info(f"✅ AI report generated for {project_id}")
                except Exception as e:
                    logger.error(f"LLM error for {project_id}: {e}")
                    ai_report = f"Report generation temporarily unavailable. Please try again later.\n\nError: {str(e)}"
            else:
                ai_report = "AI report generation is currently unavailable. Please check configuration."
            
            return {
                'success': True,
                'data': {
                    'report': ai_report,
                    'generated': ai_report is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating report for {project_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def custom_query(self, project_id: str, query: str) -> Dict[str, Any]:
        """
        Section 3: Answer custom questions about the project using agent with conversation memory
        
        Args:
            project_id: Project ID
            query: User's question
            
        Returns:
            Dict with answer
        """
        try:
            # Get project details
            project_result = self.get_project_details(project_id)
            if not project_result.get('success'):
                return project_result
            
            project = project_result['data']
            
            # Use LLM to answer the question
            llm = get_llm()
            
            if llm and LANGCHAIN_AVAILABLE:
                try:
                    logger.info(f"🤖 Answering question about {project_id}: {query}")
                    
                    # MemorySaver provides thread-local conversation persistence
                    checkpointer = MemorySaver()
                    
                    # MemorySaver provides thread-local conversation persistence
                    checkpointer = MemorySaver()
                    
                    # Create agent with memory and trimming
                    project_context = f"""Project Information:
- Name: {project.get('project_name', 'Unknown')}
- ID: {project.get('project_id', 'N/A')}
- Country: {project.get('country', 'N/A')}
- Category: {project.get('category', 'N/A')}
- Methodology: {project.get('methodology', 'N/A')}
- Vintage: {project.get('vintage', 'N/A')}
- Available Credits: {project.get('available_credits', 0):,}
- Price: ${project.get('price', 0):.2f}
- Registry Status: {project.get('registry_status', 'N/A')}
- Description: {project.get('description', 'No description available')}"""
                    
                    agent = create_react_agent(
                        model=llm,
                        tools=[],
                        state_modifier=f"""You are an expert on carbon credit projects analyzing {project.get('project_name', 'this project')} ({project_id}).

CURRENT PROJECT CONTEXT:
{project_context}

Answer questions about THIS PROJECT clearly and accurately. All questions are about {project.get('project_name', 'this project')} unless stated otherwise.

If asked to compare, explain its specific strengths. Do not hallucinate data.

User's Question: {query}"""
                    )
                    
                    # Use thread_id for conversation memory per project
                    config = {"configurable": {"thread_id": project_id}}
                    
                    # Invoke agent with conversation history
                    result = agent.invoke(
                        {"messages": [HumanMessage(content=query)]},
                        config
                    )
                    
                    # Extract response - handle multimodal content
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        content = last_message.content
                        # If content is a list (multimodal), extract only text parts
                        if isinstance(content, list):
                            text_parts = [item.get('text', '') if isinstance(item, dict) else str(item) 
                                          for item in content if isinstance(item, dict) and item.get('type') == 'text']
                            answer = ' '.join(text_parts).strip()
                        else:
                            answer = str(content).strip()
                    else:
                        answer = str(last_message)
                    
                    # Convert markdown to HTML for proper formatting
                    answer_html = markdown.markdown(answer, extensions=['nl2br', 'sane_lists'])
                    
                    logger.info(f"✅ Answer generated for {project_id}")
                    
                    return {
                        'success': True,
                        'data': {
                            'answer': answer_html,
                            'question': query
                        }
                    }
                except Exception as e:
                    logger.error(f"LLM error for Q&A: {e}")
                    return {
                        'success': False,
                        'error': f'Failed to generate answer: {str(e)}'
                    }
            else:
                return {
                    'success': False,
                    'error': 'AI chat is currently unavailable. Please check configuration.'
                }
            
        except Exception as e:
            logger.error(f"Error in custom query for {project_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_report_prompt(self, project: Dict[str, Any]) -> str:
        """Create prompt for comprehensive report generation"""
        system_instructions = """You are an expert carbon credit analyst and sustainability consultant. 
Generate a comprehensive, professional report about this carbon offset project.

Your report should include:

1. **Executive Summary** (2-3 sentences)
   - Project overview and main impact
   - Key achievement or unique selling point

2. **Project Description** (2-3 detailed paragraphs)
   - Methodology and technical approach
   - Location specifics and environmental context
   - Scale of operation and implementation details

3. **Environmental Impact**
   - Carbon reduction/sequestration metrics
   - Co-benefits: biodiversity, water quality, soil health, community benefits
   - Long-term sustainability

4. **Key Metrics & Verification**
   - Available credits and vintage year
   - Registry status and certification
   - Price analysis and market positioning

5. **Investment Analysis**
   - Why this project is attractive
   - Risk factors and considerations
   - Quality indicators

Make the report professional, detailed (500-800 words), and data-driven. Use markdown formatting.
DO NOT make up numbers - use only the provided data."""
        
        return f"""{system_instructions}

Generate a comprehensive report for:

Project ID: {project.get('project_id', 'N/A')}
Project Name: {project.get('project_name', 'Unknown Project')}
Country: {project.get('country', 'N/A')}
Category: {project.get('category', 'N/A')}
Methodology: {project.get('methodology', 'N/A')}
Vintage: {project.get('vintage', 'N/A')}
Available Credits: {project.get('available_credits', 0):,}
Price per Credit: ${project.get('price', 0):.2f}
Registry Status: {project.get('registry_status', 'N/A')}
Description: {project.get('description', 'No description available')}"""
    
    def _create_qa_prompt(self, project: Dict[str, Any], query: str) -> str:
        """Create prompt for Q&A about project"""
        return f"""You are an expert on carbon credit projects. Answer the following question about this project.

Project Information:
- Name: {project.get('project_name', 'Unknown')}
- ID: {project.get('project_id', 'N/A')}
- Country: {project.get('country', 'N/A')}
- Category: {project.get('category', 'N/A')}
- Methodology: {project.get('methodology', 'N/A')}
- Vintage: {project.get('vintage', 'N/A')}
- Available Credits: {project.get('available_credits', 0):,}
- Price: ${project.get('price', 0):.2f}
- Registry Status: {project.get('registry_status', 'N/A')}
- Description: {project.get('description', 'No description available')}

User Question: {query}

Provide a clear, concise, and accurate answer based on the project data. If the question cannot be answered with the available data, say so clearly."""
