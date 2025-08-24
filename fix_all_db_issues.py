#!/usr/bin/env python3
"""
Fix All Database Issues
Fixes missing columns, tables, and checks database methods
"""

import sqlite3
import time

def fix_database_schema():
    """Fix all database schema issues."""
    try:
        print("🔧 Fixing all database schema issues...")
        time.sleep(2)  # Wait for locks to clear
        
        conn = sqlite3.connect("bot_database.db", timeout=30)
        cursor = conn.cursor()
        
        # 1. Fix destination_health table
        print("\n📍 Fixing destination_health table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_health';")
        if not cursor.fetchone():
            print("❌ destination_health table missing, creating...")
            cursor.execute('''
                CREATE TABLE destination_health (
                    destination_id TEXT PRIMARY KEY,
                    destination_name TEXT,
                    total_attempts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    last_success TIMESTAMP,
                    last_failure TIMESTAMP,
                    ban_count INTEGER DEFAULT 0,
                    last_ban_time TIMESTAMP,
                    cooldown_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Created destination_health table")
        else:
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'destination_id' not in columns:
                print("❌ destination_id missing, recreating table...")
                cursor.execute("DROP TABLE destination_health")
                cursor.execute('''
                    CREATE TABLE destination_health (
                        destination_id TEXT PRIMARY KEY,
                        destination_name TEXT,
                        total_attempts INTEGER DEFAULT 0,
                        successful_posts INTEGER DEFAULT 0,
                        failed_posts INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 100.0,
                        last_success TIMESTAMP,
                        last_failure TIMESTAMP,
                        ban_count INTEGER DEFAULT 0,
                        last_ban_time TIMESTAMP,
                        cooldown_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("✅ Recreated destination_health table")
            else:
                print("✅ destination_health table OK")
        
        # 2. Fix failed_group_joins table
        print("\n📍 Fixing failed_group_joins table...")
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        columns = [row[1] for row in cursor.fetchall()]
        
        missing_columns = []
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
            if col_name not in columns:
                missing_columns.append((col_name, col_type))
        
        for col_name, col_type in missing_columns:
            try:
                cursor.execute(f"ALTER TABLE failed_group_joins ADD COLUMN {col_name} {col_type}")
                print(f"  ✅ Added: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"  ℹ️ {col_name} already exists")
                else:
                    print(f"  ❌ Error adding {col_name}: {e}")
        
        # 3. Add updated_at to all relevant tables
        print("\n📍 Adding updated_at columns...")
        tables_needing_updated_at = [
            'ad_slots', 'admin_ad_slots', 'posting_history', 'worker_usage',
            'worker_health', 'managed_groups', 'payments'
        ]
        
        for table_name in tables_needing_updated_at:
            try:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT")
                    print(f"  ✅ Added updated_at to {table_name}")
                else:
                    print(f"  ℹ️ {table_name} already has updated_at")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"  ⚠️ Table {table_name} doesn't exist")
                else:
                    print(f"  ❌ Error with {table_name}: {e}")
        
        # 4. Check for admin_ad_slots table
        print("\n📍 Checking admin_ad_slots table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots';")
        if not cursor.fetchone():
            print("❌ admin_ad_slots table missing, creating...")
            cursor.execute('''
                CREATE TABLE admin_ad_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    destinations TEXT NOT NULL,
                    interval_minutes INTEGER DEFAULT 60,
                    last_sent_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_paused BOOLEAN DEFAULT 0,
                    pause_reason TEXT,
                    pause_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            ''')
            print("✅ Created admin_ad_slots table")
        else:
            print("✅ admin_ad_slots table exists")
        
        conn.commit()
        conn.close()
        
        print("\n✅ All database schema issues fixed!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_methods():
    """Check if database methods exist."""
    print("\n🔍 Checking database methods...")
    try:
        # Import the database manager
        from src.database.manager import DatabaseManager
        import logging
        
        logger = logging.getLogger(__name__)
        db = DatabaseManager("bot_database.db", logger)
        
        # Check if get_admin_ad_slots method exists
        if hasattr(db, 'get_admin_ad_slots'):
            print("✅ get_admin_ad_slots method exists")
        else:
            print("❌ get_admin_ad_slots method missing")
            print("💡 This method needs to be added to DatabaseManager")
            
        # Check other common methods
        methods_to_check = [
            'get_problematic_destinations',
            'update_payment_status',
            'activate_subscription',
            'record_worker_post'
        ]
        
        for method_name in methods_to_check:
            if hasattr(db, method_name):
                print(f"✅ {method_name} method exists")
            else:
                print(f"❌ {method_name} method missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database methods: {e}")
        return False

def main():
    """Main function to fix all database issues."""
    print("🚀 Starting comprehensive database fix...")
    
    # Fix schema first
    schema_ok = fix_database_schema()
    
    if schema_ok:
        print("\n" + "="*50)
        # Check methods
        methods_ok = check_database_methods()
        
        if schema_ok and methods_ok:
            print("\n🎉 Database fix completed successfully!")
            print("🔄 Restart the bot to apply changes")
        else:
            print("\n⚠️ Some issues may remain, check output above")
    else:
        print("\n❌ Database schema fix failed")

if __name__ == '__main__':
    main()
