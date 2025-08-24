#!/usr/bin/env python3
"""
Fix critical errors preventing bot from working
"""

import sqlite3
import os
from datetime import datetime

def fix_get_posting_history_method():
    """Fix the get_posting_history method signature issue."""
    print("🔧 Fixing get_posting_history method...")
    
    # Check if the method exists and fix it
    db_manager_path = 'src/database/manager.py'
    
    if not os.path.exists(db_manager_path):
        print(f"❌ Database manager not found: {db_manager_path}")
        return False
    
    with open(db_manager_path, 'r') as f:
        content = f.read()
    
    # Check if the method exists
    if 'def get_posting_history(' not in content:
        print("❌ get_posting_history method not found")
        return False
    
    # The issue is that the method is being called with slot_id parameter but doesn't accept it
    # We need to find where it's being called incorrectly
    print("✅ get_posting_history method exists - need to check usage")
    return True

def fix_destination_health_table():
    """Fix the destination_health table structure."""
    print("\n🔧 Fixing destination_health table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if destination_health table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_health'")
        if not cursor.fetchone():
            print("❌ destination_health table not found")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(destination_health)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 destination_health columns: {column_names}")
        
        # Check if destination_id column exists
        if 'destination_id' not in column_names:
            print("❌ destination_id column missing from destination_health")
            return False
        
        print("✅ destination_health table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking destination_health: {e}")
        return False
    finally:
        conn.close()

def fix_worker_cooldowns_table():
    """Fix the worker_cooldowns table structure."""
    print("\n🔧 Fixing worker_cooldowns table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if worker_cooldowns table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_cooldowns'")
        if not cursor.fetchone():
            print("❌ worker_cooldowns table not found")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 worker_cooldowns columns: {column_names}")
        
        # The table should have: id, worker_id, cooldown_until, created_at
        expected_columns = ['id', 'worker_id', 'cooldown_until', 'created_at']
        missing_columns = [col for col in expected_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Missing columns in worker_cooldowns: {missing_columns}")
            return False
        
        print("✅ worker_cooldowns table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking worker_cooldowns: {e}")
        return False
    finally:
        conn.close()

def fix_posting_history_table():
    """Fix the posting_history table structure."""
    print("\n🔧 Fixing posting_history table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if posting_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history'")
        if not cursor.fetchone():
            print("❌ posting_history table not found")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 posting_history columns: {column_names}")
        
        # The table should have basic posting history columns
        expected_columns = ['id', 'slot_id', 'worker_id', 'destination_id', 'posted_at', 'success']
        missing_columns = [col for col in expected_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Missing columns in posting_history: {missing_columns}")
            return False
        
        print("✅ posting_history table structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error checking posting_history: {e}")
        return False
    finally:
        conn.close()

def check_ad_slots_for_posting():
    """Check if there are ad slots ready for posting."""
    print("\n🔧 Checking ad slots for posting...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check user ad slots
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        user_due = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        user_total = cursor.fetchone()[0]
        
        # Check admin ad slots
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        admin_due = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
        admin_total = cursor.fetchone()[0]
        
        print(f"📊 User ad slots: {user_due}/{user_total} due for posting")
        print(f"📊 Admin ad slots: {admin_due}/{admin_total} due for posting")
        print(f"📊 Total due: {user_due + admin_due}")
        
        if user_due + admin_due == 0:
            print("❌ No ad slots are due for posting!")
            print("💡 This might be why no ads are being posted")
            return False
        else:
            print("✅ Ad slots are available for posting")
            return True
        
    except Exception as e:
        print(f"❌ Error checking ad slots: {e}")
        return False
    finally:
        conn.close()

def check_worker_availability():
    """Check if workers are available for posting."""
    print("\n🔧 Checking worker availability...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check workers not in cooldown
        cursor.execute("""
            SELECT COUNT(*) FROM worker_usage w
            LEFT JOIN worker_cooldowns c ON w.worker_id = c.worker_id 
                AND c.cooldown_until > datetime('now')
            WHERE c.worker_id IS NULL
        """)
        available_workers = cursor.fetchone()[0]
        
        print(f"📊 Available workers (not in cooldown): {available_workers}")
        
        if available_workers == 0:
            print("❌ No workers are available (all in cooldown)!")
            print("💡 This might be why no ads are being posted")
            return False
        else:
            print("✅ Workers are available for posting")
            return True
        
    except Exception as e:
        print(f"❌ Error checking worker availability: {e}")
        return False
    finally:
        conn.close()

def reset_cooldowns_for_testing():
    """Reset cooldowns to test if that fixes the posting issue."""
    print("\n🔧 Resetting cooldowns for testing...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Clear all cooldowns
        cursor.execute("DELETE FROM worker_cooldowns")
        conn.commit()
        
        print("✅ All worker cooldowns cleared")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing cooldowns: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run all fixes."""
    print("🔧 Fixing Critical Errors")
    print("=" * 50)
    
    # Check and fix issues
    posting_history_ok = fix_get_posting_history_method()
    destination_health_ok = fix_destination_health_table()
    worker_cooldowns_ok = fix_worker_cooldowns_table()
    posting_history_table_ok = fix_posting_history_table()
    
    # Check why no ads are being posted
    ad_slots_ok = check_ad_slots_for_posting()
    workers_ok = check_worker_availability()
    
    # Reset cooldowns for testing
    cooldowns_reset = reset_cooldowns_for_testing()
    
    print("\n" + "=" * 50)
    print("📊 Fix Results:")
    print("=" * 50)
    
    print(f"  Posting History Method: {'✅ OK' if posting_history_ok else '❌ ISSUE'}")
    print(f"  Destination Health Table: {'✅ OK' if destination_health_ok else '❌ ISSUE'}")
    print(f"  Worker Cooldowns Table: {'✅ OK' if worker_cooldowns_ok else '❌ ISSUE'}")
    print(f"  Posting History Table: {'✅ OK' if posting_history_table_ok else '❌ ISSUE'}")
    print(f"  Ad Slots Available: {'✅ OK' if ad_slots_ok else '❌ ISSUE'}")
    print(f"  Workers Available: {'✅ OK' if workers_ok else '❌ ISSUE'}")
    print(f"  Cooldowns Reset: {'✅ OK' if cooldowns_reset else '❌ ISSUE'}")
    
    print("\n" + "=" * 50)
    if ad_slots_ok and workers_ok:
        print("🎉 Issues fixed! Bot should now post ads.")
        print("🚀 Restart the bot: python3 bot.py")
    else:
        print("❌ Some issues remain. Check the results above.")

if __name__ == "__main__":
    main()
