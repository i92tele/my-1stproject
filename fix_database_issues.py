#!/usr/bin/env python3
"""
Fix Database Issues - Schema and Constraints
"""

import sqlite3
import time

def fix_database_issues():
    """Fix database schema and constraint issues."""
    try:
        # Wait a moment for any locks to clear
        print("⏳ Waiting for database locks to clear...")
        time.sleep(2)
        
        conn = sqlite3.connect("bot_database.db", timeout=30)
        cursor = conn.cursor()
        
        print("🔧 Fixing database issues...")
        
        # Check failed_group_joins table structure
        print("\n🔍 Checking failed_group_joins table...")
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        columns_info = cursor.fetchall()
        columns = [row[1] for row in columns_info]
        print(f"📋 Current columns: {columns}")
        
        # Check for constraints
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='failed_group_joins';")
        create_sql = cursor.fetchone()
        if create_sql:
            print(f"📋 Table structure: {create_sql[0]}")
        
        # Check if group_id has UNIQUE constraint
        has_unique_constraint = create_sql and 'UNIQUE' in create_sql[0] and 'group_id' in create_sql[0]
        
        if has_unique_constraint:
            print("⚠️ found UNIQUE constraint on group_id, removing it...")
            
            # Get existing data
            cursor.execute("SELECT * FROM failed_group_joins")
            existing_data = cursor.fetchall()
            print(f"📊 Found {len(existing_data)} existing records")
            
            # Drop and recreate table without UNIQUE constraint
            cursor.execute("DROP TABLE failed_group_joins")
            cursor.execute('''
                CREATE TABLE failed_group_joins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT,
                    group_name TEXT,
                    group_username TEXT,
                    fail_reason TEXT,
                    fail_count INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    workers_tried TEXT,
                    priority INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    worker_id INTEGER,
                    error TEXT
                )
            ''')
            print("✅ Recreated failed_group_joins table without UNIQUE constraint")
            
            # Restore data (removing duplicates)
            if existing_data:
                seen_groups = set()
                unique_data = []
                for row in existing_data:
                    group_id = row[1] if len(row) > 1 else None  # group_id is second column
                    if group_id and group_id not in seen_groups:
                        seen_groups.add(group_id)
                        unique_data.append(row[1:])  # Skip the old id
                
                if unique_data:
                    placeholders = ','.join(['?' * (len(unique_data[0]))])
                    cursor.executemany(f"INSERT INTO failed_group_joins VALUES (NULL, {placeholders})", unique_data)
                    print(f"✅ Restored {len(unique_data)} unique records")
        else:
            print("✅ No problematic UNIQUE constraint found")
        
        # Add missing columns if they don't exist
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        current_columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = {
            'worker_id': 'INTEGER',
            'error': 'TEXT',
            'fail_reason': 'TEXT',
            'fail_count': 'INTEGER DEFAULT 0',
            'last_attempt': 'TIMESTAMP',
            'workers_tried': 'TEXT',
            'priority': 'INTEGER DEFAULT 0',
            'notes': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in current_columns:
                try:
                    cursor.execute(f"ALTER TABLE failed_group_joins ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ Added: {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"  ℹ️ {col_name} already exists")
                    else:
                        print(f"  ❌ Error adding {col_name}: {e}")
        
        # Add updated_at to other tables that need it
        tables_needing_updated_at = [
            'ad_slots', 'admin_ad_slots', 'posting_history', 'worker_usage',
            'worker_health', 'destination_health', 'managed_groups'
        ]
        
        print(f"\n🔧 Adding updated_at columns to other tables...")
        for table_name in tables_needing_updated_at:
            try:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    print(f"  ✅ Added updated_at to {table_name}")
                else:
                    print(f"  ℹ️ {table_name} already has updated_at")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"  ⚠️ Table {table_name} doesn't exist")
                else:
                    print(f"  ❌ Error with {table_name}: {e}")
        
        # Check final structure
        print(f"\n📋 Final failed_group_joins structure:")
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"Columns: {final_columns}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database issues fixed!")
        print("🎯 The bot should now work without database errors!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_database_issues()
