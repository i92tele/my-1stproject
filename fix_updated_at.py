#!/usr/bin/env python3
"""
Fix updated_at Column Issues
"""

import sqlite3

def fix_updated_at():
    """Add updated_at column to all tables that need it."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Adding updated_at columns to all relevant tables...")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found tables: {tables}")
        
        # Tables that should have updated_at column
        tables_needing_updated_at = [
            'ad_slots',
            'admin_ad_slots', 
            'admin_slot_posts',
            'ad_posts',
            'posting_history',
            'destination_health',
            'worker_usage',
            'worker_health',
            'worker_bans',
            'worker_activity_log',
            'failed_group_joins',
            'managed_groups',
            'slot_destinations',
            'admin_slot_destinations',
            'payments',
            'users',
            'worker_limits',
            'notification_log'
        ]
        
        for table_name in tables_needing_updated_at:
            if table_name in tables:
                print(f"\n🔧 Checking table: {table_name}")
                
                # Check current columns
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                        print(f"  ✅ Added updated_at to {table_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            print(f"  ℹ️ updated_at already exists in {table_name}")
                        else:
                            print(f"  ❌ Error adding updated_at to {table_name}: {e}")
                else:
                    print(f"  ℹ️ updated_at already exists in {table_name}")
            else:
                print(f"  ⚠️ Table {table_name} doesn't exist")
        
        print("\n🔍 Checking specific tables mentioned in errors...")
        
        # Check specific tables that are causing errors
        error_tables = ['ad_slots', 'admin_ad_slots', 'posting_history', 'worker_usage']
        for table_name in error_tables:
            if table_name in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"📋 {table_name} columns: {columns}")
                
                if 'updated_at' not in columns:
                    print(f"❌ {table_name} is missing updated_at column!")
                else:
                    print(f"✅ {table_name} has updated_at column")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Updated_at column fix completed!")
        print("🎯 All tables should now have updated_at columns!")
        
    except Exception as e:
        print(f"❌ Error fixing updated_at columns: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_updated_at()
