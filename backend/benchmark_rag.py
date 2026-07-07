import time
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from services.news_rag_service import search_news
from services.projects_rag_service import search_projects
from llm_manager import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

def evaluate_relevance(llm, query: str, context: str) -> bool:
    """Uses LLM-as-a-judge to evaluate if context answers the query."""
    if not llm:
        return False
        
    sys_prompt = "You are a strict evaluator. Does the provided context sufficiently answer the search query? Answer with exactly one word: YES or NO."
    human_prompt = f"Query: {query}\n\nContext: {context}"
    
    try:
        response = llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        content = str(response.content).strip().upper()
        return "YES" in content
    except Exception as e:
        print(f"LLM eval error: {e}")
        return False

def run_benchmark(output_file: str):
    print(f"Starting RAG Benchmark. Results will be saved to {output_file}")
    
    news_queries = [
        "Tesla ESG rating and sustainability efforts",
        "Microsoft carbon neutrality goals 2030",
        "European green deal carbon border adjustment",
        "Apple Scope 3 emissions reduction",
        "Renewable energy investments in Q3"
    ]
    
    project_queries = [
        "Wind energy projects in India",
        "REDD+ deforestation projects in Brazil",
        "Solar power rural electrification Africa",
        "Methane capture from landfills",
        "Blue carbon mangrove restoration"
    ]
    
    llm = get_llm()
    if not llm:
        print("Warning: LLM not available. Relevance will be marked as False.")
    
    results = {
        "news": {"total_time": 0, "avg_time": 0, "relevance_score": 0, "queries": []},
        "projects": {"total_time": 0, "avg_time": 0, "relevance_score": 0, "queries": []}
    }
    
    # Benchmark News RAG
    print("\n--- Benchmarking News RAG ---")
    news_hits = 0
    for q in news_queries:
        start_time = time.time()
        chunks = search_news(q, k=3)
        latency = time.time() - start_time
        
        context = "\n".join([c.get('content', '') for c in chunks])
        is_relevant = evaluate_relevance(llm, q, context)
        if is_relevant:
            news_hits += 1
            
        print(f"Query: '{q[:30]}...' | Latency: {latency:.3f}s | Relevant: {is_relevant}")
        
        results["news"]["queries"].append({
            "query": q,
            "latency": latency,
            "relevant": is_relevant,
            "num_chunks": len(chunks)
        })
        results["news"]["total_time"] += latency
        
    if len(news_queries) > 0:
        results["news"]["avg_time"] = results["news"]["total_time"] / len(news_queries)
        results["news"]["relevance_score"] = (news_hits / len(news_queries)) * 100
    
    # Benchmark Projects RAG
    print("\n--- Benchmarking Projects RAG ---")
    project_hits = 0
    for q in project_queries:
        start_time = time.time()
        chunks = search_projects(q, k=3)
        latency = time.time() - start_time
        
        context = "\n".join([c.get('content', '') if isinstance(c, dict) else str(c) for c in chunks])
        is_relevant = evaluate_relevance(llm, q, context)
        if is_relevant:
            project_hits += 1
            
        print(f"Query: '{q[:30]}...' | Latency: {latency:.3f}s | Relevant: {is_relevant}")
        
        results["projects"]["queries"].append({
            "query": q,
            "latency": latency,
            "relevant": is_relevant,
            "num_chunks": len(chunks)
        })
        results["projects"]["total_time"] += latency
        
    if len(project_queries) > 0:
        results["projects"]["avg_time"] = results["projects"]["total_time"] / len(project_queries)
        results["projects"]["relevance_score"] = (project_hits / len(project_queries)) * 100
    
    # Overall summary
    print("\n=== BENCHMARK SUMMARY ===")
    print(f"News RAG     -> Avg Latency: {results['news']['avg_time']:.3f}s | Relevance: {results['news']['relevance_score']}%")
    print(f"Projects RAG -> Avg Latency: {results['projects']['avg_time']:.3f}s | Relevance: {results['projects']['relevance_score']}%")
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved benchmark results to {output_file}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "benchmark_baseline.json"
    run_benchmark(out_file)
