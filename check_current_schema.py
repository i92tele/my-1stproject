#!/usr/bin/env python3
"""
Check Current Database Schema
Identify the missing chat_id column issue in worker_activity_log
"""

import sqlite3
import os

def main():
    """Main function."""
    print("🔍 CHECKING CURRENT DATABASE SCHEMA")
    print("=" * 50)
    
    try:
        # Connect to database
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check worker_activity_log table
        print("\n📋 WORKER_ACTIVITY_LOG TABLE:")
        print("-" * 40)
        
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
        
        print(f"\n📊 CURRENT COLUMNS:")
        for col in columns:
            col_id, name, type_name, not_null, default_val, primary_key = col
            print(f"  • {name} ({type_name})")
        
        # Check for chat_id column
        column_names = [col[1] for col in columns]
        if 'chat_id' not in column_names:
            print(f"\n❌ MISSING: chat_id column")
            print(f"✅ PRESENT: destination_id column" if 'destination_id' in column_names else "❌ MISSING: destination_id column")
        else:
            print(f"\n✅ chat_id column exists")
        
        # Check recent errors in logs
        print(f"\n🔍 RECENT ACTIVITY LOGS:")
        print("-" * 40)
        
        try:
            cursor.execute("SELECT COUNT(*) FROM worker_activity_log")
            count = cursor.fetchone()[0]
            print(f"Total records: {count}")
            
            if count > 0:
                cursor.execute("SELECT * FROM worker_activity_log ORDER BY created_at DESC LIMIT 3")
                recent = cursor.fetchall()
                
                for i, record in enumerate(recent, 1):
                    print(f"\nRecord {i}:")
                    for j, col in enumerate(columns):
                        print(f"  {col[1]}: {record[j]}")
        except Exception as e:
            print(f"❌ Error reading worker_activity_log: {e}")
        
        # Check what the code is trying to insert
        print(f"\n🔍 CODE ANALYSIS:")
        print("-" * 40)
        print("The error shows the code is trying to insert 'chat_id' but the table has 'destination_id'")
        print("This suggests a column name mismatch in the code.")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
