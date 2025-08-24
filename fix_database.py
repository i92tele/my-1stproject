#!/usr/bin/env python3
"""
Fix Database - Add missing columns and fix database issues
"""

import sqlite3

def fix_database():
    """Fix missing database columns and issues."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Fixing database issues...")
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Existing tables: {tables}")
        
        # Check worker_usage table structure
        if 'worker_usage' in tables:
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Worker usage columns: {columns}")
            
            # Add missing columns
            missing_columns = []
            
            if 'messages_sent_today' not in columns:
                missing_columns.append('messages_sent_today INTEGER DEFAULT 0')
            
            if 'messages_sent_this_hour' not in columns:
                missing_columns.append('messages_sent_this_hour INTEGER DEFAULT 0')
            
            if 'last_reset_date' not in columns:
                missing_columns.append('last_reset_date TEXT')
            
            if 'last_reset_hour' not in columns:
                missing_columns.append('last_reset_hour INTEGER')
            
            # Add missing columns
            for column_def in missing_columns:
                column_name = column_def.split()[0]
                try:
                    cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {column_def}")
                    print(f"  ✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"  ℹ️ Column {column_name} already exists")
                    else:
                        print(f"  ❌ Error adding {column_name}: {e}")
        else:
            print("❌ worker_usage table not found")
        
        # Check destinations table structure
        if 'destinations' in tables:
            cursor.execute("PRAGMA table_info(destinations);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Destinations columns: {columns}")
            
            # Add missing columns
            if 'destination_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE destinations ADD COLUMN destination_id INTEGER PRIMARY KEY AUTOINCREMENT")
                    print("  ✅ Added column: destination_id")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding destination_id: {e}")
        
        # Check admin_ad_slots table structure
        if 'admin_ad_slots' in tables:
            cursor.execute("PRAGMA table_info(admin_ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Admin ad slots columns: {columns}")
            
            # Add missing columns
            if 'is_paused' not in columns:
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN is_paused INTEGER DEFAULT 0")
                    print("  ✅ Added column: is_paused")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding is_paused: {e}")
            
            if 'pause_reason' not in columns:
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN pause_reason TEXT")
                    print("  ✅ Added column: pause_reason")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding pause_reason: {e}")
            
            if 'pause_time' not in columns:
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN pause_time TEXT")
                    print("  ✅ Added column: pause_time")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding pause_time: {e}")
            
            if 'updated_at' not in columns:
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN updated_at TEXT")
                    print("  ✅ Added column: updated_at")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding updated_at: {e}")
        
        # Check ad_slots table structure
        if 'ad_slots' in tables:
            cursor.execute("PRAGMA table_info(ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Ad slots columns: {columns}")
            
            # Add missing columns
            if 'updated_at' not in columns:
                try:
                    cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TEXT")
                    print("  ✅ Added column: updated_at")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding updated_at: {e}")
        
        conn.commit()
        conn.close()
        
        print("✅ Database fixes completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_database()
