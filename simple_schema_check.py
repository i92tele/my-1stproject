#!/usr/bin/env python3
"""
Simple Schema Check
Check the worker_activity_log table schema using a simple approach
"""

import sqlite3
import os

def main():
    """Main function."""
    print("🔍 SIMPLE SCHEMA CHECK")
    print("=" * 30)
    
    try:
        # Connect to database directly
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if worker_activity_log table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='worker_activity_log'
        """)
        
        if not cursor.fetchone():
            print("❌ worker_activity_log table doesn't exist")
            return
        
        print("✅ worker_activity_log table exists")
        
        # Get table schema
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        
        print(f"\n📋 COLUMNS IN WORKER_ACTIVITY_LOG:")
        print("-" * 30)
        
        for col in columns:
            col_id, name, type_name, not_null, default_val, primary_key = col
            print(f"{name} ({type_name})")
        
        # Get sample data
        cursor.execute("SELECT * FROM worker_activity_log LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print(f"\n📊 SAMPLE DATA:")
            print("-" * 30)
            for i, col in enumerate(columns):
                print(f"{col[1]}: {sample[i]}")
        
        # Find worker phone column
        worker_phone_col = None
        for col in columns:
            if 'phone' in col[1].lower() or 'worker' in col[1].lower():
                worker_phone_col = col[1]
                break
        
        if worker_phone_col:
            print(f"\n✅ Found worker phone column: {worker_phone_col}")
        else:
            print(f"\n❌ No worker phone column found")
            print("Available columns:")
            for col in columns:
                print(f"  - {col[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
