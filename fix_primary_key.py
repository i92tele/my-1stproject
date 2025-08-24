#!/usr/bin/env python3
"""
Fix Primary Key Issue in failed_group_joins
"""

import sqlite3

def fix_primary_key():
    """Fix the primary key issue in failed_group_joins table."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Fixing failed_group_joins primary key issue...")
        
        # Get existing data
        cursor.execute("SELECT * FROM failed_group_joins")
        existing_data = cursor.fetchall()
        print(f"📊 Found {len(existing_data)} existing records")
        
        # Drop and recreate table with proper structure
        cursor.execute("DROP TABLE failed_group_joins")
        cursor.execute('''
            CREATE TABLE failed_group_joins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                group_name TEXT,
                group_username TEXT,
                fail_reason TEXT,
                fail_count INTEGER DEFAULT 1,
                last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                workers_tried TEXT,
                priority TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                worker_id INTEGER,
                error TEXT
            )
        ''')
        print("✅ Recreated failed_group_joins with auto-incrementing id as primary key")
        
        # Restore data
        if existing_data:
            for row in existing_data:
                # Insert without the old primary key constraint issue
                cursor.execute('''
                    INSERT INTO failed_group_joins 
                    (group_id, group_name, group_username, fail_reason, fail_count, 
                     last_attempt, workers_tried, priority, notes, created_at, 
                     updated_at, worker_id, error) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', row)
            print(f"✅ Restored {len(existing_data)} records")
        
        # Check final structure
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Final columns: {columns}")
        
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='failed_group_joins';")
        create_sql = cursor.fetchone()
        print(f"📋 Final structure: {create_sql[0]}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Primary key issue fixed!")
        print("🎯 Multiple records can now be added for the same group_id!")
        
    except Exception as e:
        print(f"❌ Error fixing primary key: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_primary_key()
