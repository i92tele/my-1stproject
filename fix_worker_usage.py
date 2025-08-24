#!/usr/bin/env python3
"""
Fix Worker Usage Table

This script specifically fixes the worker_usage table created_at column issue.
"""

import sqlite3
import sys

def fix_worker_usage_table():
    """Fix the worker_usage table created_at column."""
    try:
        print("🔧 Fixing worker_usage table...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check if worker_usage table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage';")
        if not cursor.fetchone():
            print("❌ worker_usage table doesn't exist!")
            return False
        
        # Check current columns
        cursor.execute("PRAGMA table_info(worker_usage);")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Check if created_at column exists
        if 'created_at' not in columns:
            print("❌ created_at column missing, adding it...")
            try:
                cursor.execute("ALTER TABLE worker_usage ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                print("✅ Successfully added created_at column")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding created_at column: {e}")
                return False
        else:
            print("✅ created_at column already exists")
        
        # Check if date column exists
        if 'date' not in columns:
            print("❌ date column missing, adding it...")
            try:
                cursor.execute("ALTER TABLE worker_usage ADD COLUMN date TEXT")
                print("✅ Successfully added date column")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding date column: {e}")
                return False
        else:
            print("✅ date column already exists")
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(worker_usage);")
        columns_after = [row[1] for row in cursor.fetchall()]
        print(f"📋 Columns after fix: {columns_after}")
        
        # Test creating a record
        try:
            cursor.execute('''
                INSERT INTO worker_usage 
                (worker_id, date, messages_sent_today, created_at) 
                VALUES (999, '2025-08-19', 0, CURRENT_TIMESTAMP)
            ''')
            print("✅ Successfully created test record")
            
            # Clean up
            cursor.execute("DELETE FROM worker_usage WHERE worker_id = 999")
            print("✅ Cleaned up test record")
        except Exception as e:
            print(f"❌ Error creating test record: {e}")
            return False
        
        conn.commit()
        conn.close()
        
        print("✅ worker_usage table fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing worker_usage table: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("WORKER USAGE TABLE FIX")
    print("=" * 50)
    
    success = fix_worker_usage_table()
    
    if success:
        print("\n🎉 WORKER USAGE TABLE FIXED!")
        sys.exit(0)
    else:
        print("\n❌ WORKER USAGE TABLE FIX FAILED!")
        sys.exit(1)
