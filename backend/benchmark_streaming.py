import time
import json
import psycopg2
from kafka import KafkaConsumer
import threading
import os
import sys

DB_HOST = "postgres"
DB_PORT = "5432"
DB_NAME = "carbon_intel"
DB_USER = "carbon"
DB_PASSWORD = "carbonpw"
KAFKA_SERVER = "kafka:9092"
TOPIC = "carbon.public.finance"
FILE_PATH = "/app/carbon-intelligence/server/output/finance.jsonl"

def benchmark():
    print("==================================================")
    print("🚀 STARTING STREAMING BENCHMARK")
    print("==================================================")
    
    # 1. Setup Kafka consumer
    print("📡 Connecting to Kafka...")
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=KAFKA_SERVER,
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        sys.exit(1)
        
    kafka_time = [None]
    def listen_kafka():
        for message in consumer:
            if message.value and isinstance(message.value, dict):
                payload = message.value.get("payload", {})
                if payload and isinstance(payload, dict):
                    after = payload.get("after", {})
                    if after and isinstance(after, dict) and after.get("ticker") == "BENCH":
                        kafka_time[0] = time.time()
                        break
                
    threading.Thread(target=listen_kafka, daemon=True).start()
    print("   ✓ Kafka listener ready")
    
    # 2. Setup File watcher
    print("📂 Connecting to Pathway JSONL output...")
    file_time = [None]
    def tail_file():
        while True:
            if os.path.exists(FILE_PATH):
                with open(FILE_PATH, 'r') as f:
                    content = f.read()
                    if "BENCH" in content:
                        file_time[0] = time.time()
                        break
            time.sleep(0.1)
    
    threading.Thread(target=tail_file, daemon=True).start()
    print("   ✓ File watcher ready")
    
    time.sleep(2) # Give threads time to initialize
    
    # 3. Insert into Postgres
    print("\n⏳ Committing transaction to PostgreSQL...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()
    
    # Delete first just in case
    cur.execute("DELETE FROM finance WHERE ticker = 'BENCH'")
    conn.commit()
    
    start_time = time.time()
    cur.execute("""
        INSERT INTO finance (
            ticker, company_name, industry, description, gii_score, stock_price, 
            market_cap, sustainability_update, esg_rating, website, price, volume, 
            change_percent, timestamp
        ) 
        VALUES (
            'BENCH', 'BENCHMARK_COMPANY', 'Tech', 'Desc', 100, 50.0, 
            '1B', 'Update', 'A', 'web', 50.0, 1000, 
            1.0, 1234567890
        )
    """)
    conn.commit()
    db_commit_time = time.time()
    
    # Wait for both events
    max_wait = 30
    wait_start = time.time()
    print("⏳ Waiting for streaming pipeline to propagate...")
    while (kafka_time[0] is None or file_time[0] is None) and (time.time() - wait_start) < max_wait:
        time.sleep(0.01)
        
    print("\n==================================================")
    print("🎉 BENCHMARK RESULTS")
    print("==================================================")
    
    print(f"1. Database Insert:     {(db_commit_time - start_time) * 1000:7.2f} ms")
    
    if kafka_time[0]:
        print(f"2. Debezium + Kafka:    {(kafka_time[0] - db_commit_time) * 1000:7.2f} ms (CDC Propagation)")
    else:
        print("❌ Did not receive Kafka message in time.")
        
    if file_time[0] and kafka_time[0]:
        print(f"3. Pathway Processing:  {(file_time[0] - kafka_time[0]) * 1000:7.2f} ms (Kafka -> JSONL)")
    elif file_time[0]:
        print(f"3. Pathway Processing:  {(file_time[0] - db_commit_time) * 1000:7.2f} ms (from DB)")
    else:
        print("❌ Did not receive File change in time.")
        
    if file_time[0]:
        print(f"\n⚡ Total Pipeline Latency: {(file_time[0] - db_commit_time) * 1000:.2f} ms")
        print("==================================================")
        
    # Clean up
    cur.execute("DELETE FROM finance WHERE ticker = 'BENCH'")
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    benchmark()
