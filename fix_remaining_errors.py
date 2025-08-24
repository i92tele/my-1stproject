#!/usr/bin/env python3
"""
Fix Remaining Database Errors - Fix all the specific errors mentioned
"""

import sqlite3
import os
from datetime import datetime

def fix_worker_cooldowns_table():
    """Fix worker_cooldowns table to include is_active column."""
    print("🔧 Fixing worker_cooldowns table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current worker_cooldowns columns: {column_names}")
        
        # Check if is_active column exists
        if 'is_active' not in column_names:
            print("📝 Adding is_active column to worker_cooldowns...")
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("✅ Added is_active column")
        else:
            print("✅ is_active column already exists")
        
        # Check if last_used_at column exists
        if 'last_used_at' not in column_names:
            print("📝 Adding last_used_at column to worker_cooldowns...")
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN last_used_at TEXT")
            print("✅ Added last_used_at column")
        else:
            print("✅ last_used_at column already exists")
        
        # Update all existing records to have is_active = 1
        cursor.execute("UPDATE worker_cooldowns SET is_active = 1 WHERE is_active IS NULL")
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        final_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 Final worker_cooldowns columns: {final_columns}")
        
        required_columns = ['id', 'worker_id', 'cooldown_until', 'created_at', 'is_active', 'last_used_at']
        missing_columns = [col for col in required_columns if col not in final_columns]
        
        if missing_columns:
            print(f"❌ Still missing columns: {missing_columns}")
            return False
        else:
            print("✅ worker_cooldowns table structure is correct")
            return True
        
    except Exception as e:
        print(f"❌ Error fixing worker_cooldowns table: {e}")
        return False
    finally:
        conn.close()

def fix_worker_activity_log_table():
    """Fix worker_activity_log table to include destination_id column."""
    print("\n🔧 Fixing worker_activity_log table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_activity_log'")
        if not cursor.fetchone():
            print("❌ worker_activity_log table does not exist - creating it")
            cursor.execute('''
                CREATE TABLE worker_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    destination_id TEXT,
                    destination_name TEXT,
                    action TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.commit()
            print("✅ worker_activity_log table created")
            return True
        
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current worker_activity_log columns: {column_names}")
        
        # Check if destination_id column exists
        if 'destination_id' not in column_names:
            print("📝 Adding destination_id column to worker_activity_log...")
            cursor.execute("ALTER TABLE worker_activity_log ADD COLUMN destination_id TEXT")
            print("✅ Added destination_id column")
        else:
            print("✅ destination_id column already exists")
        
        # Check if destination_name column exists
        if 'destination_name' not in column_names:
            print("📝 Adding destination_name column to worker_activity_log...")
            cursor.execute("ALTER TABLE worker_activity_log ADD COLUMN destination_name TEXT")
            print("✅ Added destination_name column")
        else:
            print("✅ destination_name column already exists")
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        final_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 Final worker_activity_log columns: {final_columns}")
        
        required_columns = ['id', 'worker_id', 'destination_id', 'destination_name', 'action', 'success', 'error_message', 'created_at']
        missing_columns = [col for col in required_columns if col not in final_columns]
        
        if missing_columns:
            print(f"❌ Still missing columns: {missing_columns}")
            return False
        else:
            print("✅ worker_activity_log table structure is correct")
            return True
        
    except Exception as e:
        print(f"❌ Error fixing worker_activity_log table: {e}")
        return False
    finally:
        conn.close()

def fix_posting_history_table():
    """Fix posting_history table to include ban_detected column."""
    print("\n🔧 Fixing posting_history table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current structure
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current posting_history columns: {column_names}")
        
        # Check if ban_detected column exists
        if 'ban_detected' not in column_names:
            print("📝 Adding ban_detected column to posting_history...")
            cursor.execute("ALTER TABLE posting_history ADD COLUMN ban_detected BOOLEAN DEFAULT 0")
            print("✅ Added ban_detected column")
        else:
            print("✅ ban_detected column already exists")
        
        # Check if ban_type column exists
        if 'ban_type' not in column_names:
            print("📝 Adding ban_type column to posting_history...")
            cursor.execute("ALTER TABLE posting_history ADD COLUMN ban_type TEXT")
            print("✅ Added ban_type column")
        else:
            print("✅ ban_type column already exists")
        
        # Check if error_message column exists
        if 'error_message' not in column_names:
            print("📝 Adding error_message column to posting_history...")
            cursor.execute("ALTER TABLE posting_history ADD COLUMN error_message TEXT")
            print("✅ Added error_message column")
        else:
            print("✅ error_message column already exists")
        
        # Check if message_content_hash column exists
        if 'message_content_hash' not in column_names:
            print("📝 Adding message_content_hash column to posting_history...")
            cursor.execute("ALTER TABLE posting_history ADD COLUMN message_content_hash TEXT")
            print("✅ Added message_content_hash column")
        else:
            print("✅ message_content_hash column already exists")
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(posting_history)")
        final_columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 Final posting_history columns: {final_columns}")
        
        required_columns = ['id', 'slot_id', 'worker_id', 'destination_id', 'destination_name', 'posted_at', 'success', 'ban_detected', 'ban_type', 'error_message', 'message_content_hash']
        missing_columns = [col for col in required_columns if col not in final_columns]
        
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

def verify_all_fixes():
    """Verify that all fixes are working correctly."""
    print("\n🔧 Verifying all fixes...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test worker_cooldowns query
        print("📍 Testing worker_cooldowns query...")
        cursor.execute('''
            SELECT 
                wc.worker_id,
                wc.is_active,
                wc.last_used_at,
                wc.created_at,
                COALESCE(wu.messages_sent_today, 0) as messages_today,
                COALESCE(wu.daily_limit, 50) as daily_limit
            FROM worker_cooldowns wc
            LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                AND wu.date = date('now')
            ORDER BY wc.worker_id
            LIMIT 5
        ''')
        workers = cursor.fetchall()
        print(f"✅ worker_cooldowns query works: {len(workers)} workers found")
        
        # Test worker_activity_log query
        print("📍 Testing worker_activity_log query...")
        cursor.execute('''
            SELECT destination_id, destination_name, 
                   COUNT(*) as error_count
            FROM worker_activity_log
            WHERE success = 0 
            AND created_at > datetime('now', '-24 hours')
            GROUP BY destination_id, destination_name
            HAVING error_count > 0
            ORDER BY error_count DESC
            LIMIT 5
        ''')
        problematic = cursor.fetchall()
        print(f"✅ worker_activity_log query works: {len(problematic)} problematic destinations found")
        
        # Test posting_history query
        print("📍 Testing posting_history query...")
        cursor.execute('''
            SELECT * FROM posting_history 
            WHERE ban_detected = 1
            ORDER BY posted_at DESC
            LIMIT 5
        ''')
        banned_posts = cursor.fetchall()
        print(f"✅ posting_history query works: {len(banned_posts)} banned posts found")
        
        print("✅ All database queries working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run comprehensive error fix."""
    print("🔧 FIXING REMAINING DATABASE ERRORS")
    print("=" * 50)
    print("⚠️  Fixing all specific errors mentioned...")
    print("=" * 50)
    
    # Fix all tables
    cooldowns_ok = fix_worker_cooldowns_table()
    activity_log_ok = fix_worker_activity_log_table()
    posting_history_ok = fix_posting_history_table()
    
    # Verify fixes
    verification_ok = verify_all_fixes()
    
    print("\n" + "=" * 50)
    print("📊 FIX RESULTS:")
    print("=" * 50)
    
    print(f"  Worker Cooldowns Table: {'✅ FIXED' if cooldowns_ok else '❌ FAILED'}")
    print(f"  Worker Activity Log Table: {'✅ FIXED' if activity_log_ok else '❌ FAILED'}")
    print(f"  Posting History Table: {'✅ FIXED' if posting_history_ok else '❌ FAILED'}")
    print(f"  Verification: {'✅ SUCCESS' if verification_ok else '❌ FAILED'}")
    
    print("\n" + "=" * 50)
    if cooldowns_ok and activity_log_ok and posting_history_ok and verification_ok:
        print("🎉 ALL ERRORS FIXED!")
        print("✅ No more 'wc.is_active' errors")
        print("✅ No more 'destination_id' errors")
        print("✅ No more 'ban_detected' errors")
        print("✅ All database queries working correctly")
        print("\n🚀 SAFE TO START BOT")
        print("📝 Expected behavior:")
        print("  • No more database column errors")
        print("  • Workers will be available for posting")
        print("  • Ads will be posted successfully")
    else:
        print("❌ SOME ERRORS REMAIN")
        print("⚠️  Fix the failed items before starting bot")

if __name__ == "__main__":
    main()

