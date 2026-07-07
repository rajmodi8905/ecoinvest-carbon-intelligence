import time
import json
import os
import sys

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from services.project_report_service import ProjectReportService
from services.company_service import CompanyService
# pyrefly: ignore [missing-import]
from pathway_reader import PathwayDataReader

def main():
    print("Starting Report Generation Benchmark...")
    
    output_file = "benchmark_generation_baseline.json"
    
    # Initialize services
    print("Loading data reader...")
    reader = PathwayDataReader()
    
    print("Initializing services...")
    project_svc = ProjectReportService(reader)
    company_svc = CompanyService(reader)
    
    results = {}
    
    # 1. Benchmark Project Report Generation
    test_project_id = "VCS-191" # Example project
    print(f"\n--- Benchmarking Project Report ({test_project_id}) ---")
    start_time = time.time()
    
    try:
        # Force refresh to bypass cache
        res = project_svc.generate_project_report(test_project_id, force_refresh=True)
        latency = time.time() - start_time
        
        if res.get('success'):
            words = len(res['data']['report'].split())
            print(f"✅ Success! Latency: {latency:.2f}s | Words generated: {words}")
            results['project_report'] = {'latency_seconds': latency, 'words': words, 'success': True}
        else:
            print(f"❌ Failed: {res.get('error')}")
            results['project_report'] = {'latency_seconds': latency, 'success': False, 'error': res.get('error')}
    except Exception as e:
        print(f"❌ Exception: {e}")
        
    # 2. Benchmark Company Future Impact Generation
    test_company_ticker = "TSLA"
    print(f"\n--- Benchmarking Company Future Impact ({test_company_ticker}) ---")
    start_time = time.time()
    
    try:
        res = company_svc.get_future_impact_analysis(test_company_ticker, force_refresh=True)
        latency = time.time() - start_time
        
        if res.get('success'):
            words = len(res['data']['analysis'].split())
            print(f"✅ Success! Latency: {latency:.2f}s | Words generated: {words}")
            results['company_impact'] = {'latency_seconds': latency, 'words': words, 'success': True}
        else:
            print(f"❌ Failed: {res.get('error')}")
            results['company_impact'] = {'latency_seconds': latency, 'success': False, 'error': res.get('error')}
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\n💾 Saved results to {output_file}")

if __name__ == "__main__":
    main()
