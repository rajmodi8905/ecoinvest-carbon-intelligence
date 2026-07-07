import os
import sys
import time
import json
from pathlib import Path

# Need to insert backend dir into path to run as script
backend_dir = str(Path(__file__).parent.absolute())
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Override LLM mode for benchmark
os.environ["LLM_MODE"] = "ollama"

def run_microsoft_benchmark():
    print("🚀 Starting Microsoft Company Impact Benchmark...")
    print("Loading data reader...")
    
    start_init = time.time()
    from pathway_reader import PathwayDataReader
    reader = PathwayDataReader()
    
    print("Initializing services...")
    from services.company_service import CompanyService
    company_service = CompanyService(pathway_reader=reader)
    
    # RAG services are initialized automatically on first search
    
    print(f"✅ Initialization complete in {time.time() - start_init:.2f}s")
    
    ticker = "MSFT"
    print(f"\n📊 Benchmarking: Microsoft Corporation ({ticker})")
    
    print("🤖 Triggering generate_future_impact (this tests all sections)...")
    
    start_total = time.time()
    result = company_service.get_future_impact_analysis(ticker, force_refresh=True)
    total_time = time.time() - start_total
    
    print("\n" + "="*50)
    print("🎉 BENCHMARK RESULTS")
    print("="*50)
    
    if result.get('success'):
        data = result.get('data', {})
        timings = data.get('timings', {})
        
        print(f"Total Latency: {total_time:.2f}s")
        print("\nBreakdown:")
        print(f"1. News RAG Fetch:     {timings.get('news_rag', 0):.2f}s")
        print(f"2. Projects RAG Fetch: {timings.get('projects_rag', 0):.2f}s")
        print(f"3. Finance API Fetch:  {timings.get('finance_api', 0):.2f}s")
        print(f"4. LLM Generation:     {timings.get('llm_generation', 0):.2f}s")
        print(f"5. Overhead:           {total_time - sum(timings.values()):.2f}s")
        
        print("\n📝 Output sample:")
        print(data.get('analysis', '')[:300] + "...")
        
        # Save to benchmark file
        benchmark_file = os.path.join(backend_dir, "benchmark_microsoft_timing.json")
        with open(benchmark_file, "w") as f:
            json.dump({
                "ticker": ticker,
                "total_time": total_time,
                "timings": timings,
                "output_preview": data.get('analysis', '')[:300]
            }, f, indent=4)
        print(f"\n💾 Saved full timing results to {benchmark_file}")
    else:
        print("❌ Benchmark failed!")
        print(result)

if __name__ == "__main__":
    run_microsoft_benchmark()
