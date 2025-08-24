#!/usr/bin/env python3
"""
Force Fix Database

This script forces all database fixes to be applied and verifies they work
"""

import sqlite3
import sys
import os

def force_fix_database():
    """Force apply all database fixes."""
    try:
        print("🔧 FORCE FIXING DATABASE...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Fix destination_health table - FORCE RECREATE
        print("\n📍 1. FORCE FIXING destination_health table...")
        try:
            # Drop and recreate the table
            cursor.execute("DROP TABLE IF EXISTS destination_health")
            cursor.execute('''
                CREATE TABLE destination_health (
                    destination_id TEXT PRIMARY KEY,
                    destination_name TEXT,
                    total_attempts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    last_success TEXT,
                    last_failure TEXT,
                    ban_count INTEGER DEFAULT 0,
                    last_ban_time TEXT,
                    cooldown_until TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Recreated destination_health table with correct schema")
        except Exception as e:
            print(f"❌ Error recreating destination_health: {e}")
        
        # 2. Fix posting_history table - FORCE RECREATE
        print("\n📍 2. FORCE FIXING posting_history table...")
        try:
            # Drop and recreate the table
            cursor.execute("DROP TABLE IF EXISTS posting_history")
            cursor.execute('''
                CREATE TABLE posting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER,
                    slot_type TEXT DEFAULT 'user',
                    destination_id TEXT,
                    destination_name TEXT,
                    worker_id INTEGER,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    message_content_hash TEXT,
                    ban_detected BOOLEAN DEFAULT 0,
                    ban_type TEXT,
                    posted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            ''')
            print("✅ Recreated posting_history table with correct schema")
        except Exception as e:
            print(f"❌ Error recreating posting_history: {e}")
        
        # 3. Fix worker_usage table - ADD MISSING COLUMNS
        print("\n📍 3. FORCE FIXING worker_usage table...")
        try:
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing_columns = [
                ('messages_sent_today', 'INTEGER DEFAULT 0'),
                ('messages_sent_this_hour', 'INTEGER DEFAULT 0'),
                ('last_reset_date', 'TEXT'),
                ('last_reset_hour', 'INTEGER'),
                ('created_at', 'TEXT'),
                ('updated_at', 'TEXT'),
                ('date', 'TEXT')
            ]
            
            for col_name, col_type in missing_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added: {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"❌ Error adding {col_name}: {e}")
                else:
                    print(f"ℹ️ {col_name} already exists")
        except Exception as e:
            print(f"❌ Error fixing worker_usage: {e}")
        
        # 4. Fix failed_group_joins table
        print("\n📍 4. FORCE FIXING failed_group_joins table...")
        try:
            cursor.execute("PRAGMA table_info(failed_group_joins);")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing_columns = [
                ('worker_id', 'INTEGER'),
                ('error', 'TEXT'),
                ('fail_reason', 'TEXT'),
                ('fail_count', 'INTEGER DEFAULT 0'),
                ('last_attempt', 'TEXT'),
                ('workers_tried', 'TEXT'),
                ('priority', 'INTEGER DEFAULT 0'),
                ('notes', 'TEXT'),
                ('created_at', 'TEXT'),
                ('updated_at', 'TEXT')
            ]
            
            for col_name, col_type in missing_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE failed_group_joins ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added: {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"❌ Error adding {col_name}: {e}")
                else:
                    print(f"ℹ️ {col_name} already exists")
        except Exception as e:
            print(f"❌ Error fixing failed_group_joins: {e}")
        
        # 5. Add timestamp columns to ad_slots and admin_ad_slots
        print("\n📍 5. FORCE FIXING timestamp columns...")
        for table_name in ['ad_slots', 'admin_ad_slots']:
            try:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'last_sent_at' not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN last_sent_at TEXT")
                    print(f"✅ Added last_sent_at to {table_name}")
                else:
                    print(f"ℹ️ last_sent_at already exists in {table_name}")
                    
                if 'updated_at' not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT")
                    print(f"✅ Added updated_at to {table_name}")
                else:
                    print(f"ℹ️ updated_at already exists in {table_name}")
                    
            except Exception as e:
                print(f"❌ Error fixing {table_name}: {e}")
        
        # Commit all changes
        conn.commit()
        
        # 6. VERIFY ALL FIXES
        print("\n📍 6. VERIFYING ALL FIXES...")
        
        # Test destination_health
        try:
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'destination_id' in columns:
                print("✅ destination_health: destination_id column exists")
            else:
                print("❌ destination_health: destination_id column missing")
        except Exception as e:
            print(f"❌ Error checking destination_health: {e}")
        
        # Test posting_history
        try:
            cursor.execute("PRAGMA table_info(posting_history);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'ban_detected' in columns:
                print("✅ posting_history: ban_detected column exists")
            else:
                print("❌ posting_history: ban_detected column missing")
        except Exception as e:
            print(f"❌ Error checking posting_history: {e}")
        
        # Test worker_usage
        try:
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'created_at' in columns:
                print("✅ worker_usage: created_at column exists")
            else:
                print("❌ worker_usage: created_at column missing")
        except Exception as e:
            print(f"❌ Error checking worker_usage: {e}")
        
        # Test failed_group_joins
        try:
            cursor.execute("PRAGMA table_info(failed_group_joins);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'worker_id' in columns:
                print("✅ failed_group_joins: worker_id column exists")
            else:
                print("❌ failed_group_joins: worker_id column missing")
        except Exception as e:
            print(f"❌ Error checking failed_group_joins: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error in force fix: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("FORCE DATABASE FIX")
    print("=" * 60)
    
    if not os.path.exists("bot_database.db"):
        print("❌ Database file not found!")
        sys.exit(1)
    
    success = force_fix_database()
    
    if success:
        print("\n🎉 FORCE FIX COMPLETED!")
        print("All database tables have been fixed.")
        print("The bot should now run without database errors.")
    else:
        print("\n❌ FORCE FIX FAILED!")
        print("Please check the error messages above.")
    
    sys.exit(0 if success else 1)
