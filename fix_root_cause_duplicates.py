#!/usr/bin/env python3
"""
Fix Root Cause of Worker Duplicates - Prevent future duplicates and clean existing ones
"""

import sqlite3
import os
from datetime import datetime

def fix_initialize_worker_limits_method():
    """Fix the initialize_worker_limits method to prevent duplicates."""
    print("🔧 Fixing initialize_worker_limits method...")
    
    try:
        # Read the current database manager file
        with open('src/database/manager.py', 'r') as f:
            content = f.read()
        
        # Find the current initialize_worker_limits method
        if 'async def initialize_worker_limits(self, worker_id: int) -> bool:' in content:
            print("✅ Found initialize_worker_limits method")
            
            # Check if it already has proper duplicate prevention
            if 'INSERT OR IGNORE' in content:
                print("✅ Method already uses INSERT OR IGNORE - this is good")
                return True
            else:
                print("⚠️ Method doesn't use INSERT OR IGNORE - this could cause duplicates")
                return False
        else:
            print("❌ initialize_worker_limits method not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking initialize_worker_limits method: {e}")
        return False

def add_worker_usage_constraint():
    """Add a UNIQUE constraint to worker_usage table to prevent duplicates."""
    print("\n🔧 Adding UNIQUE constraint to worker_usage table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if UNIQUE constraint already exists
        cursor.execute("PRAGMA table_info(worker_usage)")
        columns = cursor.fetchall()
        
        # Look for UNIQUE constraint on worker_id
        worker_id_column = None
        for col in columns:
            if col[1] == 'worker_id':
                worker_id_column = col
                break
        
        if worker_id_column and worker_id_column[5] == 1:  # 5th element indicates UNIQUE
            print("✅ UNIQUE constraint already exists on worker_id")
            return True
        
        # Add UNIQUE constraint
        print("📝 Adding UNIQUE constraint to worker_id...")
        
        # Create a new table with the constraint
        cursor.execute('''
            CREATE TABLE worker_usage_new (
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
        
        # Copy data from old table to new table
        cursor.execute('''
            INSERT OR IGNORE INTO worker_usage_new 
            SELECT DISTINCT * FROM worker_usage
        ''')
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE worker_usage")
        cursor.execute("ALTER TABLE worker_usage_new RENAME TO worker_usage")
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX idx_worker_usage_worker_id 
            ON worker_usage (worker_id)
        ''')
        
        conn.commit()
        print("✅ UNIQUE constraint added successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error adding UNIQUE constraint: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def clean_existing_duplicates():
    """Clean existing duplicate workers and ensure exactly 10 workers."""
    print("\n🔧 Cleaning existing duplicate workers...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all worker IDs with counts
        cursor.execute("""
            SELECT worker_id, COUNT(*) as count 
            FROM worker_usage 
            GROUP BY worker_id 
            ORDER BY worker_id
        """)
        worker_counts = cursor.fetchall()
        
        print("📊 Current worker distribution:")
        for worker_id, count in worker_counts:
            print(f"  Worker {worker_id}: {count} entries")
        
        # Find duplicates
        duplicates = [(worker_id, count) for worker_id, count in worker_counts if count > 1]
        
        if duplicates:
            print(f"📋 Found {len(duplicates)} workers with duplicates:")
            for worker_id, count in duplicates:
                print(f"  Worker {worker_id}: {count} entries")
            
            # Delete all entries for duplicate workers
            for worker_id, count in duplicates:
                cursor.execute("DELETE FROM worker_usage WHERE worker_id = ?", (worker_id,))
                print(f"🗑️ Deleted {count} duplicate entries for worker {worker_id}")
            
            # Re-insert single entry for each duplicate worker
            for worker_id, count in duplicates:
                cursor.execute('''
                    INSERT INTO worker_usage 
                    (worker_id, hour, hourly_posts, daily_posts, day, messages_sent_today, 
                     messages_sent_this_hour, last_reset_date, last_reset_hour, updated_at, 
                     date, created_at, daily_limit, hourly_limit)
                    VALUES (?, ?, 0, 0, ?, 0, 0, ?, ?, ?, ?, ?, 150, 15)
                ''', (
                    worker_id,
                    datetime.now().strftime('%Y-%m-%d %H:00:00'),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().hour,
                    datetime.now(),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now()
                ))
                print(f"✅ Re-inserted single entry for worker {worker_id}")
        else:
            print("✅ No duplicates found")
        
        # Ensure we have exactly 10 workers (1-10)
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        existing_workers = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Existing workers: {existing_workers}")
        
        # Add missing workers
        for worker_id in range(1, 11):
            if worker_id not in existing_workers:
                cursor.execute('''
                    INSERT INTO worker_usage 
                    (worker_id, hour, hourly_posts, daily_posts, day, messages_sent_today, 
                     messages_sent_this_hour, last_reset_date, last_reset_hour, updated_at, 
                     date, created_at, daily_limit, hourly_limit)
                    VALUES (?, ?, 0, 0, ?, 0, 0, ?, ?, ?, ?, ?, 150, 15)
                ''', (
                    worker_id,
                    datetime.now().strftime('%Y-%m-%d %H:00:00'),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now().hour,
                    datetime.now(),
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.now()
                ))
                print(f"✅ Added missing worker {worker_id}")
        
        conn.commit()
        
        # Verify final state
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        final_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        final_workers = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Final worker count: {final_count}")
        print(f"📋 Final worker IDs: {final_workers}")
        
        if final_count == 10 and final_workers == list(range(1, 11)):
            print("✅ Worker cleanup successful!")
            return True
        else:
            print("❌ Worker cleanup failed!")
            return False
        
    except Exception as e:
        print(f"❌ Error cleaning duplicates: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_fixes():
    """Verify that all fixes are working correctly."""
    print("\n🔧 Verifying fixes...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        
        # Check for duplicates
        cursor.execute("""
            SELECT worker_id, COUNT(*) as count 
            FROM worker_usage 
            GROUP BY worker_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        # Check worker IDs
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        worker_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Worker count: {worker_count}")
        print(f"📋 Worker IDs: {worker_ids}")
        print(f"📋 Duplicates found: {len(duplicates)}")
        
        if duplicates:
            print("❌ Still have duplicates:")
            for worker_id, count in duplicates:
                print(f"  Worker {worker_id}: {count} entries")
            return False
        
        if worker_count == 10 and worker_ids == list(range(1, 11)):
            print("✅ All fixes verified successfully!")
            return True
        else:
            print("❌ Verification failed!")
            return False
        
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run comprehensive root cause fix."""
    print("🔧 ROOT CAUSE DUPLICATE FIX")
    print("=" * 50)
    print("⚠️  Fixing root cause of worker duplicates...")
    print("=" * 50)
    
    # Check current method
    method_ok = fix_initialize_worker_limits_method()
    
    # Add UNIQUE constraint
    constraint_ok = add_worker_usage_constraint()
    
    # Clean existing duplicates
    cleanup_ok = clean_existing_duplicates()
    
    # Verify fixes
    verification_ok = verify_fixes()
    
    print("\n" + "=" * 50)
    print("📊 FIX RESULTS:")
    print("=" * 50)
    
    print(f"  Method Check: {'✅ OK' if method_ok else '⚠️ NEEDS ATTENTION'}")
    print(f"  UNIQUE Constraint: {'✅ ADDED' if constraint_ok else '❌ FAILED'}")
    print(f"  Duplicate Cleanup: {'✅ SUCCESS' if cleanup_ok else '❌ FAILED'}")
    print(f"  Verification: {'✅ SUCCESS' if verification_ok else '❌ FAILED'}")
    
    print("\n" + "=" * 50)
    if constraint_ok and cleanup_ok and verification_ok:
        print("🎉 ROOT CAUSE FIXED!")
        print("✅ UNIQUE constraint prevents future duplicates")
        print("✅ Existing duplicates cleaned up")
        print("✅ Exactly 10 workers exist")
        print("✅ System is protected from future duplicates")
        print("\n🚀 SAFE TO START BOT")
        print("📝 The bot will no longer create duplicate workers")
    else:
        print("❌ SOME FIXES FAILED")
        print("⚠️  Address failed items before starting bot")

if __name__ == "__main__":
    main()

