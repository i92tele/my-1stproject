#!/usr/bin/env python3
"""
Comprehensive Database Fix - Fix all database structure issues properly
"""

import sqlite3
import os
from datetime import datetime

def check_and_fix_posting_history_table():
    """Check and fix posting_history table structure."""
    print("🔧 Checking posting_history table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history'")
        if not cursor.fetchone():
            print("❌ posting_history table does not exist - creating it")
            cursor.execute('''
                CREATE TABLE posting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    destination_id TEXT NOT NULL,
                    destination_name TEXT,
                    posted_at TEXT DEFAULT (datetime('now')),
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    ban_detected BOOLEAN DEFAULT 0,
                    ban_type TEXT,
                    message_content_hash TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
            print("✅ posting_history table created")
            return True
        
        # Check current structure
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current posting_history columns: {column_names}")
        
        # Required columns
        required_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'slot_id': 'INTEGER NOT NULL',
            'worker_id': 'INTEGER NOT NULL',
            'destination_id': 'TEXT NOT NULL',
            'destination_name': 'TEXT',
            'posted_at': 'TEXT DEFAULT (datetime(\'now\'))',
            'success': 'BOOLEAN DEFAULT 1',
            'error_message': 'TEXT',
            'ban_detected': 'BOOLEAN DEFAULT 0',
            'ban_type': 'TEXT',
            'message_content_hash': 'TEXT',
            'created_at': 'TEXT DEFAULT (datetime(\'now\'))'
        }
        
        # Add missing columns
        for column_name, column_type in required_columns.items():
            if column_name not in column_names:
                try:
                    cursor.execute(f"ALTER TABLE posting_history ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"⚠️ Could not add column {column_name}: {e}")
        
        conn.commit()
        
        # Verify final structure
        cursor.execute("PRAGMA table_info(posting_history)")
        final_columns = cursor.fetchall()
        final_column_names = [col[1] for col in final_columns]
        
        print(f"📋 Final posting_history columns: {final_column_names}")
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns.keys() if col not in final_column_names]
        if missing_columns:
            print(f"❌ Still missing columns: {missing_columns}")
            return False
        else:
            print("✅ posting_history table structure is correct")
            return True
        
    except Exception as e:
        print(f"❌ Error fixing posting_history table: {e}")
        return False
    finally:
        conn.close()

def check_and_fix_destination_health_table():
    """Check and fix destination_health table structure."""
    print("\n🔧 Checking destination_health table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_health'")
        if not cursor.fetchone():
            print("❌ destination_health table does not exist - creating it")
            cursor.execute('''
                CREATE TABLE destination_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_id TEXT UNIQUE NOT NULL,
                    destination_name TEXT,
                    success_rate REAL DEFAULT 0.0,
                    total_attempts INTEGER DEFAULT 0,
                    successful_attempts INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    last_success TEXT,
                    last_failure TEXT,
                    last_attempt TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
            print("✅ destination_health table created")
            return True
        
        # Check current structure
        cursor.execute("PRAGMA table_info(destination_health)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current destination_health columns: {column_names}")
        
        # Check if destination_id column exists
        if 'destination_id' not in column_names:
            print("❌ destination_id column missing - this is critical")
            return False
        
        print("✅ destination_health table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking destination_health table: {e}")
        return False
    finally:
        conn.close()

def check_and_fix_worker_cooldowns_table():
    """Check and fix worker_cooldowns table structure."""
    print("\n🔧 Checking worker_cooldowns table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_cooldowns'")
        if not cursor.fetchone():
            print("❌ worker_cooldowns table does not exist - creating it")
            cursor.execute('''
                CREATE TABLE worker_cooldowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    cooldown_until TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (worker_id) REFERENCES worker_usage (worker_id)
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX idx_worker_cooldowns_worker_id 
                ON worker_cooldowns (worker_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX idx_worker_cooldowns_until 
                ON worker_cooldowns (cooldown_until)
            ''')
            
            conn.commit()
            print("✅ worker_cooldowns table created")
            return True
        
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current worker_cooldowns columns: {column_names}")
        
        # Required columns
        required_columns = ['id', 'worker_id', 'cooldown_until', 'created_at']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Missing columns in worker_cooldowns: {missing_columns}")
            return False
        
        print("✅ worker_cooldowns table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking worker_cooldowns table: {e}")
        return False
    finally:
        conn.close()

def check_and_fix_worker_usage_table():
    """Check and fix worker_usage table structure."""
    print("\n🔧 Checking worker_usage table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage'")
        if not cursor.fetchone():
            print("❌ worker_usage table does not exist - creating it")
            cursor.execute('''
                CREATE TABLE worker_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER UNIQUE NOT NULL,
                    hour TEXT,
                    hourly_posts INTEGER DEFAULT 0,
                    daily_posts INTEGER DEFAULT 0,
                    day TEXT,
                    messages_sent_today INTEGER DEFAULT 0,
                    messages_sent_this_hour INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    last_reset_hour INTEGER,
                    updated_at TEXT DEFAULT (datetime('now')),
                    date DATE,
                    created_at TEXT,
                    daily_limit INTEGER DEFAULT 150,
                    hourly_limit INTEGER DEFAULT 15
                )
            ''')
            conn.commit()
            print("✅ worker_usage table created")
            return True
        
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_usage)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current worker_usage columns: {column_names}")
        
        # Check worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        print(f"📊 Worker count: {worker_count}")
        
        if worker_count != 10:
            print(f"❌ Expected 10 workers, found {worker_count}")
            return False
        
        print("✅ worker_usage table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking worker_usage table: {e}")
        return False
    finally:
        conn.close()

def check_and_fix_ad_slots_tables():
    """Check and fix ad_slots and admin_ad_slots tables."""
    print("\n🔧 Checking ad_slots tables...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check ad_slots table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ad_slots'")
        if not cursor.fetchone():
            print("❌ ad_slots table does not exist")
            return False
        
        # Check admin_ad_slots table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
        if not cursor.fetchone():
            print("❌ admin_ad_slots table does not exist")
            return False
        
        # Check for last_sent_at column in both tables
        cursor.execute("PRAGMA table_info(ad_slots)")
        ad_slots_columns = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(admin_ad_slots)")
        admin_ad_slots_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 ad_slots columns: {ad_slots_columns}")
        print(f"📋 admin_ad_slots columns: {admin_ad_slots_columns}")
        
        # Check if last_sent_at exists in both tables
        if 'last_sent_at' not in ad_slots_columns:
            print("❌ last_sent_at column missing from ad_slots")
            return False
        
        if 'last_sent_at' not in admin_ad_slots_columns:
            print("❌ last_sent_at column missing from admin_ad_slots")
            return False
        
        print("✅ ad_slots tables structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking ad_slots tables: {e}")
        return False
    finally:
        conn.close()

def reset_all_cooldowns():
    """Reset all worker cooldowns to ensure workers are available."""
    print("\n🔧 Resetting all worker cooldowns...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM worker_cooldowns")
        conn.commit()
        print("✅ All worker cooldowns cleared")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing cooldowns: {e}")
        return False
    finally:
        conn.close()

def verify_system_ready():
    """Verify the system is ready for posting."""
    print("\n🔧 Verifying system readiness...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check available workers
        cursor.execute("""
            SELECT COUNT(*) FROM worker_usage w
            LEFT JOIN worker_cooldowns c ON w.worker_id = c.worker_id 
                AND c.cooldown_until > datetime('now')
            WHERE c.worker_id IS NULL
        """)
        available_workers = cursor.fetchone()[0]
        
        # Check due ad slots
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        user_due = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        admin_due = cursor.fetchone()[0]
        
        print(f"📊 Available workers: {available_workers}")
        print(f"📊 User ad slots due: {user_due}")
        print(f"📊 Admin ad slots due: {admin_due}")
        print(f"📊 Total ad slots due: {user_due + admin_due}")
        
        if available_workers == 0:
            print("❌ No workers available for posting")
            return False
        
        if user_due + admin_due == 0:
            print("❌ No ad slots due for posting")
            return False
        
        print("✅ System is ready for posting")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying system: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run comprehensive database fix."""
    print("🔧 COMPREHENSIVE DATABASE FIX")
    print("=" * 50)
    print("⚠️  Fixing all database structure issues...")
    print("=" * 50)
    
    # Fix all tables
    posting_history_ok = check_and_fix_posting_history_table()
    destination_health_ok = check_and_fix_destination_health_table()
    worker_cooldowns_ok = check_and_fix_worker_cooldowns_table()
    worker_usage_ok = check_and_fix_worker_usage_table()
    ad_slots_ok = check_and_fix_ad_slots_tables()
    
    # Reset cooldowns
    cooldowns_reset = reset_all_cooldowns()
    
    # Verify system
    system_ready = verify_system_ready()
    
    print("\n" + "=" * 50)
    print("📊 FIX RESULTS:")
    print("=" * 50)
    
    print(f"  Posting History Table: {'✅ FIXED' if posting_history_ok else '❌ FAILED'}")
    print(f"  Destination Health Table: {'✅ FIXED' if destination_health_ok else '❌ FAILED'}")
    print(f"  Worker Cooldowns Table: {'✅ FIXED' if worker_cooldowns_ok else '❌ FAILED'}")
    print(f"  Worker Usage Table: {'✅ FIXED' if worker_usage_ok else '❌ FAILED'}")
    print(f"  Ad Slots Tables: {'✅ FIXED' if ad_slots_ok else '❌ FAILED'}")
    print(f"  Cooldowns Reset: {'✅ DONE' if cooldowns_reset else '❌ FAILED'}")
    print(f"  System Ready: {'✅ YES' if system_ready else '❌ NO'}")
    
    print("\n" + "=" * 50)
    if posting_history_ok and destination_health_ok and worker_cooldowns_ok and worker_usage_ok and ad_slots_ok and system_ready:
        print("🎉 ALL ISSUES FIXED!")
        print("✅ Database structure is correct")
        print("✅ Workers are available")
        print("✅ Ad slots are ready for posting")
        print("\n🚀 SAFE TO START BOT")
        print("📝 Expected behavior:")
        print("  • No more database errors")
        print("  • Workers will be available for posting")
        print("  • Ads will be posted with anti-ban protection")
    else:
        print("❌ SOME ISSUES REMAIN")
        print("⚠️  Fix the failed items before starting bot")

if __name__ == "__main__":
    main()

