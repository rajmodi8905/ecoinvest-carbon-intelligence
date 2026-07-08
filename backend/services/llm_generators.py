import json
import logging
from typing import Iterator
from llm_manager import get_llm
from langchain_core.messages import HumanMessage
from services.db_cache import get_cached_insight, set_cached_insight

logger = logging.getLogger(__name__)

def generate_company_swot_stream(ticker: str, company_info: dict) -> Iterator[str]:
    """
    Streams a sustainability-focused SWOT analysis for a company.
    Yields Server-Sent Events (SSE) format data.
    Uses Postgres ai_insights_cache for instant <50ms repeat loads.
    """
    cached = get_cached_insight("company", ticker, "swot", expiry_hours=24)
    if cached:
        yield f"data: {json.dumps({'content': cached})}\n\n"
        yield f"data: [DONE]\n\n"
        return

    llm = get_llm()
    if not llm:
        yield f"data: {json.dumps({'content': 'LLM is not available.'})}\n\n"
        return

    company_name = company_info.get('company_name', ticker)
    industry = company_info.get('industry', 'Unknown')
    desc = company_info.get('description', '')
    esg_rating = company_info.get('esg_rating', 'Unknown')

    prompt = f"""
    You are an expert ESG and sustainability financial analyst.
    Please conduct a highly focused 2x2 Sustainability SWOT analysis for {company_name} ({ticker}).
    Industry: {industry}
    
    Structure your response strictly with these markdown headings:
    ### Strengths
    ### Weaknesses
    ### Opportunities
    ### Threats
    
    CRITICAL: Keep EACH section to exactly ONE short bullet point. Be extremely concise. Focus entirely on environmental, social, and governance (ESG) factors.
    """

    try:
        messages = [HumanMessage(content=prompt)]
        full_text = []
        for chunk in llm.stream(messages):
            if chunk.content:
                full_text.append(chunk.content)
                yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        if full_text:
            set_cached_insight("company", ticker, "swot", "".join(full_text))
        yield f"data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error streaming SWOT: {e}")
        error_msg = f"\\n\\nError generating analysis: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg})}\n\n"


def generate_project_impact_stream(project_id: str, project_info: dict) -> Iterator[str]:
    """
    Streams a real-world impact translation for a carbon offset project.
    Yields Server-Sent Events (SSE) format data.
    Uses Postgres ai_insights_cache for instant <50ms repeat loads.
    """
    cached = get_cached_insight("project", project_id, "impact", expiry_hours=48)
    if cached:
        yield f"data: {json.dumps({'content': cached})}\n\n"
        yield f"data: [DONE]\n\n"
        return

    llm = get_llm()
    if not llm:
        yield f"data: {json.dumps({'content': 'LLM is not available.'})}\n\n"
        return

    name = project_info.get('name', 'Carbon Project')
    category = project_info.get('category', 'Unknown')
    country = project_info.get('country', 'Unknown')
    credits = project_info.get('available_credits', 0)
    desc = project_info.get('description', '')

    prompt = f"""
    You are an expert environmental scientist.
    Project Name: {name}
    Category: {category}
    Available Credits: {credits} tonnes of CO2e
    
    Write EXACTLY ONE extremely short paragraph (max 3 sentences) translating this project's carbon offset volume ({credits} tonnes) into highly tangible, real-world equivalents (e.g., passenger cars driven for a year, homes powered). Include a brief mention of the expected local ecological co-benefits.
    CRITICAL: Do not exceed 3 sentences. Do not use markdown headings. Be concise.
    """

    try:
        messages = [HumanMessage(content=prompt)]
        full_text = []
        for chunk in llm.stream(messages):
            if chunk.content:
                full_text.append(chunk.content)
                yield f"data: {json.dumps({'content': chunk.content})}\n\n"
        if full_text:
            set_cached_insight("project", project_id, "impact", "".join(full_text))
        yield f"data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error streaming Impact: {e}")
        error_msg = f"\\n\\nError generating analysis: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg})}\n\n"

