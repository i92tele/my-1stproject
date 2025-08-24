#!/usr/bin/env python3
"""
Check the actual structure of worker_usage table
"""

import sqlite3
import os

def check_worker_usage_structure():
    """Check the structure of worker_usage table."""
    db_path = 'bot_database.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get table info
        cursor.execute("PRAGMA table_info(worker_usage)")
        columns = cursor.fetchall()
        
        print("📋 worker_usage table structure:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - Default: {col[4]}")
        
        # Show sample data
        cursor.execute("SELECT * FROM worker_usage LIMIT 3")
        sample_data = cursor.fetchall()
        
        print(f"\n📊 Sample data ({len(sample_data)} rows):")
        for row in sample_data:
            print(f"  {row}")
        
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_worker_usage_structure()
