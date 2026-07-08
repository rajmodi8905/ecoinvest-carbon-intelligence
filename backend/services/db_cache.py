import psycopg2
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME", "carbon_intel"),
            user=os.getenv("DB_USER", "carbon"),
            password=os.getenv("DB_PASSWORD", "carbonpw"),
            host=os.getenv("DB_HOST", "postgres"),
            port=int(os.getenv("DB_PORT", 5432))
        )
    except Exception as e:
        logger.error(f"Error connecting to DB for cache: {e}")
        return None

def get_cached_insight(entity_type: str, entity_id: str, insight_type: str, expiry_hours: int = 12) -> Optional[str]:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT content FROM ai_insights_cache
                WHERE entity_type = %s AND entity_id = %s AND insight_type = %s
                AND generated_at > NOW() - INTERVAL '{expiry_hours} hours'
                ORDER BY generated_at DESC LIMIT 1
            """, (entity_type, entity_id, insight_type))
            result = cursor.fetchone()
            if result:
                logger.info(f"🟢 CACHE HIT for {entity_type} {entity_id} ({insight_type})")
                return result[0]
        return None
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        return None
    finally:
        conn.close()

def set_cached_insight(entity_type: str, entity_id: str, insight_type: str, content: str):
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ai_insights_cache (entity_type, entity_id, insight_type, content)
                VALUES (%s, %s, %s, %s)
            """, (entity_type, entity_id, insight_type, content))
        conn.commit()
        logger.info(f"💾 CACHED new {insight_type} for {entity_type} {entity_id}")
    except Exception as e:
        logger.error(f"Error writing cache: {e}")
    finally:
        conn.close()
