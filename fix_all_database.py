#!/usr/bin/env python3
"""
Fix All Database Schema Issues
"""

import sqlite3

def fix_all_database():
    """Fix all database schema issues."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Fixing all database schema issues...")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found tables: {tables}")
        
        # Fix worker_usage table
        if 'worker_usage' in tables:
            print("\n🔧 Fixing worker_usage table...")
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing_columns = []
            if 'messages_sent_today' not in columns:
                missing_columns.append('messages_sent_today INTEGER DEFAULT 0')
            if 'messages_sent_this_hour' not in columns:
                missing_columns.append('messages_sent_this_hour INTEGER DEFAULT 0')
            if 'last_reset_date' not in columns:
                missing_columns.append('last_reset_date TEXT')
            if 'last_reset_hour' not in columns:
                missing_columns.append('last_reset_hour INTEGER')
            
            for column_def in missing_columns:
                column_name = column_def.split()[0]
                try:
                    cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {column_def}")
                    print(f"  ✅ Added: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"  ℹ️ Column {column_name} already exists")
                    else:
                        print(f"  ❌ Error adding {column_name}: {e}")
        
        # Fix ad_slots table
        if 'ad_slots' in tables:
            print("\n🔧 Fixing ad_slots table...")
            cursor.execute("PRAGMA table_info(ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'updated_at' not in columns:
                try:
                    cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TEXT")
                    print("  ✅ Added: updated_at")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding updated_at: {e}")
            else:
                print("  ℹ️ updated_at already exists")
        
        # Fix admin_ad_slots table
        if 'admin_ad_slots' in tables:
            print("\n🔧 Fixing admin_ad_slots table...")
            cursor.execute("PRAGMA table_info(admin_ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'updated_at' not in columns:
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN updated_at TEXT")
                    print("  ✅ Added: updated_at")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding updated_at: {e}")
            else:
                print("  ℹ️ updated_at already exists")
        
        # Fix failed_group_joins table
        if 'failed_group_joins' in tables:
            print("\n🔧 Fixing failed_group_joins table...")
            cursor.execute("PRAGMA table_info(failed_group_joins);")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing_columns = []
            if 'worker_id' not in columns:
                missing_columns.append('worker_id INTEGER')
            if 'error' not in columns:
                missing_columns.append('error TEXT')
            if 'fail_reason' not in columns:
                missing_columns.append('fail_reason TEXT')
            if 'fail_count' not in columns:
                missing_columns.append('fail_count INTEGER DEFAULT 0')
            if 'last_attempt' not in columns:
                missing_columns.append('last_attempt TIMESTAMP')
            if 'workers_tried' not in columns:
                missing_columns.append('workers_tried TEXT')
            if 'priority' not in columns:
                missing_columns.append('priority INTEGER DEFAULT 0')
            if 'notes' not in columns:
                missing_columns.append('notes TEXT')
            if 'created_at' not in columns:
                missing_columns.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            if 'updated_at' not in columns:
                missing_columns.append('updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            
            for column_def in missing_columns:
                column_name = column_def.split()[0]
                try:
                    cursor.execute(f"ALTER TABLE failed_group_joins ADD COLUMN {column_def}")
                    print(f"  ✅ Added: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"  ℹ️ Column {column_name} already exists")
                    else:
                        print(f"  ❌ Error adding {column_name}: {e}")
        
        # Fix destination_health table
        if 'destination_health' in tables:
            print("\n🔧 Fixing destination_health table...")
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = [
                'destination_id TEXT PRIMARY KEY',
                'destination_name TEXT',
                'total_attempts INTEGER DEFAULT 0',
                'successful_posts INTEGER DEFAULT 0',
                'failed_posts INTEGER DEFAULT 0',
                'success_rate REAL DEFAULT 100.0',
                'last_success TIMESTAMP',
                'last_failure TIMESTAMP',
                'ban_count INTEGER DEFAULT 0',
                'last_ban_time TIMESTAMP',
                'cooldown_until TIMESTAMP',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            ]
            
            for column_def in required_columns:
                column_name = column_def.split()[0]
                if column_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE destination_health ADD COLUMN {column_def}")
                        print(f"  ✅ Added: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            print(f"  ℹ️ Column {column_name} already exists")
                        else:
                            print(f"  ❌ Error adding {column_name}: {e}")
                else:
                    print(f"  ℹ️ {column_name} already exists")
        
        # Create missing tables if they don't exist
        if 'posting_history' not in tables:
            print("\n🔧 Creating posting_history table...")
            cursor.execute('''
                CREATE TABLE posting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER,
                    slot_type TEXT,
                    destination_id TEXT,
                    destination_name TEXT,
                    worker_id INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    message_content_hash TEXT,
                    ban_detected BOOLEAN,
                    ban_type TEXT,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("  ✅ Created: posting_history")
        
        if 'worker_bans' not in tables:
            print("\n🔧 Creating worker_bans table...")
            cursor.execute('''
                CREATE TABLE worker_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    ban_type TEXT,
                    ban_reason TEXT,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    estimated_unban_time TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            print("  ✅ Created: worker_bans")
        
        conn.commit()
        conn.close()
        
        print("\n✅ All database schema issues fixed!")
        print("🎯 The bot should now start without database errors!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_all_database()
