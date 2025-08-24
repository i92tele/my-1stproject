#!/usr/bin/env python3
"""
Check Database Structure
"""

import sqlite3

def check_db():
    """Check current database structure."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔍 Checking Database Structure...")
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Tables: {tables}")
        
        # Check ad_slots table
        if 'ad_slots' in tables:
            cursor.execute("PRAGMA table_info(ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"\n📋 ad_slots columns: {columns}")
            
            if 'updated_at' not in columns:
                print("❌ updated_at column missing in ad_slots")
                try:
                    cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TEXT")
                    print("✅ Added updated_at to ad_slots")
                except Exception as e:
                    print(f"❌ Error adding updated_at: {e}")
            else:
                print("✅ updated_at column exists in ad_slots")
        
        # Check admin_ad_slots table
        if 'admin_ad_slots' in tables:
            cursor.execute("PRAGMA table_info(admin_ad_slots);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"\n📋 admin_ad_slots columns: {columns}")
            
            if 'updated_at' not in columns:
                print("❌ updated_at column missing in admin_ad_slots")
                try:
                    cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN updated_at TEXT")
                    print("✅ Added updated_at to admin_ad_slots")
                except Exception as e:
                    print(f"❌ Error adding updated_at: {e}")
            else:
                print("✅ updated_at column exists in admin_ad_slots")
        
        # Check worker_usage table
        if 'worker_usage' in tables:
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"\n📋 worker_usage columns: {columns}")
        
        # Check failed_group_joins table
        if 'failed_group_joins' in tables:
            cursor.execute("PRAGMA table_info(failed_group_joins);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"\n📋 failed_group_joins columns: {columns}")
            
            if 'worker_id' not in columns:
                print("❌ worker_id column missing in failed_group_joins")
                try:
                    cursor.execute("ALTER TABLE failed_group_joins ADD COLUMN worker_id INTEGER")
                    print("✅ Added worker_id to failed_group_joins")
                except Exception as e:
                    print(f"❌ Error adding worker_id: {e}")
            else:
                print("✅ worker_id column exists in failed_group_joins")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database check completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_db()
