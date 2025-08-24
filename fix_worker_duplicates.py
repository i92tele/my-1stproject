#!/usr/bin/env python3
"""
Fix Worker Duplicates - Clean up duplicate workers and ensure exactly 10 workers
"""

import sqlite3
import os
from datetime import datetime

def clean_worker_duplicates():
    """Clean up duplicate workers and ensure exactly 10 workers exist."""
    print("🔧 Cleaning worker duplicates...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        current_count = cursor.fetchone()[0]
        print(f"📊 Current worker count: {current_count}")
        
        if current_count == 10:
            print("✅ Already have exactly 10 workers - no cleanup needed")
            return True
        
        # Get all worker IDs
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        worker_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 All worker IDs: {worker_ids}")
        
        # Find duplicates
        seen = set()
        duplicates = []
        unique_workers = []
        
        for worker_id in worker_ids:
            if worker_id in seen:
                duplicates.append(worker_id)
            else:
                seen.add(worker_id)
                unique_workers.append(worker_id)
        
        print(f"📋 Unique workers: {unique_workers}")
        print(f"📋 Duplicate workers: {duplicates}")
        
        # Delete all workers
        cursor.execute("DELETE FROM worker_usage")
        print("🗑️ Deleted all worker entries")
        
        # Insert exactly 10 workers (1-10)
        for worker_id in range(1, 11):
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
        
        conn.commit()
        
        # Verify the fix
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
        print(f"❌ Error cleaning worker duplicates: {e}")
        return False
    finally:
        conn.close()

def verify_worker_cleanup():
    """Verify that worker cleanup was successful."""
    print("\n🔧 Verifying worker cleanup...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        
        # Check worker IDs
        cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
        worker_ids = [row[0] for row in cursor.fetchall()]
        
        # Check for duplicates
        unique_workers = set(worker_ids)
        
        print(f"📊 Worker count: {worker_count}")
        print(f"📋 Worker IDs: {worker_ids}")
        print(f"📋 Unique workers: {len(unique_workers)}")
        
        if worker_count == 10 and len(unique_workers) == 10 and worker_ids == list(range(1, 11)):
            print("✅ Worker verification successful!")
            return True
        else:
            print("❌ Worker verification failed!")
            return False
        
    except Exception as e:
        print(f"❌ Error verifying worker cleanup: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run worker duplicate cleanup."""
    print("🔧 WORKER DUPLICATE CLEANUP")
    print("=" * 50)
    print("⚠️  Cleaning up duplicate workers...")
    print("=" * 50)
    
    # Clean duplicates
    cleanup_success = clean_worker_duplicates()
    
    # Verify cleanup
    verification_success = verify_worker_cleanup()
    
    print("\n" + "=" * 50)
    print("📊 CLEANUP RESULTS:")
    print("=" * 50)
    
    print(f"  Worker Cleanup: {'✅ SUCCESS' if cleanup_success else '❌ FAILED'}")
    print(f"  Verification: {'✅ SUCCESS' if verification_success else '❌ FAILED'}")
    
    print("\n" + "=" * 50)
    if cleanup_success and verification_success:
        print("🎉 WORKER CLEANUP COMPLETE!")
        print("✅ Exactly 10 workers exist")
        print("✅ No duplicates found")
        print("✅ Workers are ready for posting")
        print("\n🚀 SAFE TO START BOT")
    else:
        print("❌ WORKER CLEANUP FAILED")
        print("⚠️  Fix worker issues before starting bot")

if __name__ == "__main__":
    main()

