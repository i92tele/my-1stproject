#!/usr/bin/env python3
"""
Fix Worker Count

This script ensures you have exactly 10 workers in the worker_usage table.

Usage:
    python fix_worker_count.py
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def fix_worker_count():
    """Ensure exactly 10 workers exist in the database."""
    logger.info("🔧 Fixing worker count...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Count workers
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        
        # Get list of worker IDs
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        worker_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {worker_count} workers with IDs: {worker_ids}")
        
        if worker_count == 10:
            logger.info("✅ Worker count is already correct (10)")
        elif worker_count > 10:
            # Keep only workers 1-10
            workers_to_delete = worker_ids[10:]
            if workers_to_delete:
                placeholders = ','.join('?' for _ in workers_to_delete)
                cursor.execute(f"DELETE FROM worker_usage WHERE worker_id IN ({placeholders})", workers_to_delete)
                deleted = cursor.rowcount
                logger.info(f"✅ Deleted {deleted} excess workers: {workers_to_delete}")
        else:
            # Add missing workers
            existing_ids = set(worker_ids)
            for worker_id in range(1, 11):
                if worker_id not in existing_ids:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Check which columns exist
                    cursor.execute("PRAGMA table_info(worker_usage)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'hourly_posts' in columns and 'daily_posts' in columns:
                        cursor.execute("""
                            INSERT INTO worker_usage (
                                worker_id, hourly_posts, daily_posts, 
                                hourly_limit, daily_limit, is_active, created_at
                            ) VALUES (?, 0, 0, 15, 100, 1, ?)
                        """, (worker_id, now))
                    elif 'hourly_usage' in columns and 'daily_usage' in columns:
                        cursor.execute("""
                            INSERT INTO worker_usage (
                                worker_id, hourly_usage, daily_usage, 
                                hourly_limit, daily_limit, is_active, created_at
                            ) VALUES (?, 0, 0, 15, 100, 1, ?)
                        """, (worker_id, now))
                    else:
                        # Generic approach with minimal columns
                        cursor.execute("""
                            INSERT INTO worker_usage (worker_id, is_active, created_at) 
                            VALUES (?, 1, ?)
                        """, (worker_id, now))
                    
                    logger.info(f"✅ Added missing worker {worker_id}")
        
        # Also check worker_cooldowns table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_cooldowns'")
        if cursor.fetchone():
            # Get existing worker IDs in cooldowns
            cursor.execute("SELECT DISTINCT worker_id FROM worker_cooldowns")
            cooldown_worker_ids = [row[0] for row in cursor.fetchall()]
            
            # Add missing workers to cooldowns
            for worker_id in range(1, 11):
                if worker_id not in cooldown_worker_ids:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO worker_cooldowns (worker_id, cooldown_until, created_at, is_active)
                        VALUES (?, ?, ?, 1)
                    """, (worker_id, now, now))
                    logger.info(f"✅ Added worker {worker_id} to cooldowns table")
        
        # Verify worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        new_count = cursor.fetchone()[0]
        logger.info(f"✅ Final worker count: {new_count}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker count: {e}")
        return False

if __name__ == "__main__":
    fix_worker_count()
    print("Worker count fix completed. Please restart the bot.")
