#!/usr/bin/env python3
"""
Clean up worker_usage table - remove duplicates and ensure only 10 workers
"""

import sqlite3
import os
from datetime import datetime

def clean_worker_usage():
    """Clean up worker_usage table."""
    db_path = 'bot_database.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        current_count = cursor.fetchone()[0]
        print(f"Current worker_usage count: {current_count}")
        
        # Show duplicates
        cursor.execute("""
            SELECT worker_id, COUNT(*) as count 
            FROM worker_usage 
            GROUP BY worker_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print("Found duplicates:")
            for worker_id, count in duplicates:
                print(f"  Worker {worker_id}: {count} entries")
        
        # Delete all entries
        cursor.execute("DELETE FROM worker_usage")
        print("Deleted all worker_usage entries")
        
        # Re-insert only 10 workers
        for worker_id in range(1, 11):
            cursor.execute("""
                INSERT INTO worker_usage (worker_id, hourly_posts, daily_posts, last_posted_at)
                VALUES (?, 0, 0, NULL)
            """, (worker_id,))
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        new_count = cursor.fetchone()[0]
        print(f"New worker_usage count: {new_count}")
        
        # Show the 10 workers
        cursor.execute("SELECT worker_id, hourly_posts, daily_posts FROM worker_usage ORDER BY worker_id")
        workers = cursor.fetchall()
        print("Workers after cleanup:")
        for worker_id, hourly, daily in workers:
            print(f"  Worker {worker_id}: hourly={hourly}, daily={daily}")
        
        print("✅ Worker usage table cleaned successfully!")
        
    except Exception as e:
        print(f"❌ Error cleaning worker_usage: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_worker_usage()
