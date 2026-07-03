import os
import psycopg2
import dateutil.parser
from dotenv import load_dotenv

# Load env variables
load_dotenv('.env')

db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'carbon_intel')
db_user = os.getenv('DB_USER', 'carbon')
db_password = os.getenv('DB_PASSWORD', 'carbonpw')

def main():
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
    )
    cur = conn.cursor()
    
    cur.execute("SELECT id, published FROM news")
    rows = cur.fetchall()
    
    updated = 0
    for row_id, published in rows:
        if not published:
            continue
        try:
            new_date = dateutil.parser.parse(published).isoformat()
            if new_date != published:
                cur.execute("UPDATE news SET published = %s WHERE id = %s", (new_date, row_id))
                updated += 1
        except Exception as e:
            print(f"Failed to parse {published} for id {row_id}: {e}")
            
    conn.commit()
    print(f"✅ Successfully updated {updated} out of {len(rows)} news records.")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
