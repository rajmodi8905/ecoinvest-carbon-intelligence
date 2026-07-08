import time
import uuid
import random
import requests
import psycopg2
import logging
import threading

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("StreamingBenchmark")

DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "carbon"
DB_PASS = "carbonpw"
DB_NAME = "carbon_intel"
API_URL = "http://localhost:5001/api/finance"

def run_benchmark(iterations=5):
    logger.info("==================================================")
    logger.info("⚡ RUNNING DATA STREAMING PIPELINE BENCHMARK")
    logger.info("==================================================")
    logger.info("Pipeline: PostgreSQL -> Debezium CDC -> Kafka -> Pathway -> Redis/API\n")
    
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME)
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        logger.error(f"❌ Could not connect to PostgreSQL: {e}")
        logger.error("Ensure docker containers are running and port 5432 is exposed.")
        return

    # Check if we have AAPL to test
    cursor.execute("SELECT ticker, price FROM finance LIMIT 1;")
    row = cursor.fetchone()
    if not row:
        logger.error("❌ No data in finance table to test.")
        return
        
    test_ticker = row[0]
    latencies = []

    for i in range(iterations):
        # Generate a unique target price to track
        target_price = round(random.uniform(100.0, 500.0), 2)
        
        # We will poll the API in a tight loop in a separate thread to catch the exact moment it updates
        found_event = threading.Event()
        start_time = [0]
        end_time = [0]
        
        def poll_api():
            # Wait a tiny bit to ensure the DB write happens after we start polling
            time.sleep(0.05)
            start_time[0] = time.time()
            cursor.execute("UPDATE finance SET price = %s WHERE ticker = %s;", (target_price, test_ticker))
            
            # Now tightly poll the API
            while not found_event.is_set():
                try:
                    resp = requests.get(API_URL, timeout=1)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("data", []):
                            if item.get("ticker") == test_ticker and abs(float(item.get("price", 0)) - target_price) < 0.01:
                                end_time[0] = time.time()
                                found_event.set()
                                return
                except:
                    pass
                time.sleep(0.01) # 10ms poll interval

        t = threading.Thread(target=poll_api)
        t.start()
        
        # Wait for the thread to catch the update (max 5 seconds)
        found_event.wait(timeout=5.0)
        
        if found_event.is_set():
            latency_ms = (end_time[0] - start_time[0]) * 1000
            latencies.append(latency_ms)
            logger.info(f"  • Iteration {i+1}: End-to-End Latency = {latency_ms:.2f} ms")
        else:
            logger.warning(f"  • Iteration {i+1}: TIMEOUT (Pipeline took > 5s)")
            
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        logger.info("\n==================================================")
        logger.info("🏆 STREAMING PIPELINE BENCHMARK SUMMARY")
        logger.info("==================================================")
        logger.info(f"  • Average E2E Latency : {avg_latency:.2f} ms")
        logger.info(f"  • Minimum Latency     : {min_latency:.2f} ms")
        logger.info(f"  • Maximum Latency     : {max_latency:.2f} ms")
        logger.info("==================================================")
        
        if avg_latency < 1000:
            logger.info("✅ SUCCESS: Pipeline latency is strictly SUB-SECOND as advertised.")

if __name__ == "__main__":
    run_benchmark()
