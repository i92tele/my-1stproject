#!/usr/bin/env python3
"""
Fix Worker Count Root Problem

This script fixes the root problem by cleaning up excess workers
and ensuring only 10 workers exist in the database.
"""

import asyncio
import sqlite3
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_worker_count_root():
    """Fix the root problem by cleaning up excess workers."""
    try:
        print("🔧 FIXING ROOT PROBLEM: Excess Workers")
        print("=" * 60)
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Check current worker count
        print("📍 1. Checking current worker count...")
        cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
        total_workers = cursor.fetchone()[0]
        print(f"📊 Current total workers: {total_workers}")
        
        if total_workers <= 10:
            print("✅ Worker count is already correct (≤10)")
            conn.close()
            return True
        
        # 2. Get all worker IDs
        cursor.execute("SELECT worker_id FROM worker_cooldowns ORDER BY worker_id")
        worker_ids = [row[0] for row in cursor.fetchall()]
        print(f"📋 All worker IDs: {worker_ids}")
        
        # 3. Keep only workers 1-10
        workers_to_keep = list(range(1, 11))  # 1, 2, 3, ..., 10
        workers_to_delete = [w for w in worker_ids if w not in workers_to_keep]
        
        print(f"📋 Workers to keep: {workers_to_keep}")
        print(f"📋 Workers to delete: {workers_to_delete}")
        
        if not workers_to_delete:
            print("✅ No excess workers to delete")
            conn.close()
            return True
        
        # 4. Delete excess workers
        print(f"🗑️ 4. Deleting {len(workers_to_delete)} excess workers...")
        
        # Delete from worker_cooldowns table
        placeholders = ','.join(['?' for _ in workers_to_delete])
        cursor.execute(f"DELETE FROM worker_cooldowns WHERE worker_id IN ({placeholders})", workers_to_delete)
        deleted_cooldowns = cursor.rowcount
        
        # Delete from worker_usage table
        cursor.execute(f"DELETE FROM worker_usage WHERE worker_id IN ({placeholders})", workers_to_delete)
        deleted_usage = cursor.rowcount
        
        # Delete from any other worker-related tables
        try:
            cursor.execute(f"DELETE FROM workers WHERE worker_id IN ({placeholders})", workers_to_delete)
            deleted_workers = cursor.rowcount
        except sqlite3.OperationalError:
            # workers table might not exist
            deleted_workers = 0
        
        try:
            cursor.execute(f"DELETE FROM worker_health WHERE worker_id IN ({placeholders})", workers_to_delete)
            deleted_health = cursor.rowcount
        except sqlite3.OperationalError:
            # worker_health table might not exist
            deleted_health = 0
        
        # Commit changes
        conn.commit()
        
        print(f"✅ Deleted {deleted_cooldowns} from worker_cooldowns")
        print(f"✅ Deleted {deleted_usage} from worker_usage")
        print(f"✅ Deleted {deleted_workers} from workers")
        print(f"✅ Deleted {deleted_health} from worker_health")
        
        # 5. Verify the fix
        print("📍 5. Verifying the fix...")
        cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
        new_total = cursor.fetchone()[0]
        print(f"📊 New total workers: {new_total}")
        
        cursor.execute("SELECT worker_id FROM worker_cooldowns ORDER BY worker_id")
        remaining_workers = [row[0] for row in cursor.fetchall()]
        print(f"📋 Remaining workers: {remaining_workers}")
        
        # 6. Ensure workers 1-10 exist
        print("📍 6. Ensuring workers 1-10 exist...")
        missing_workers = [w for w in workers_to_keep if w not in remaining_workers]
        
        if missing_workers:
            print(f"📋 Adding missing workers: {missing_workers}")
            for worker_id in missing_workers:
                cursor.execute('''
                    INSERT INTO worker_cooldowns (worker_id, is_active, last_used_at, created_at)
                    VALUES (?, 1, NULL, ?)
                ''', (worker_id, datetime.now().isoformat()))
                
                cursor.execute('''
                    INSERT INTO worker_usage (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, last_reset)
                    VALUES (?, 0, 0, 15, 150, ?)
                ''', (worker_id, datetime.now().isoformat()))
        
        # Commit final changes
        conn.commit()
        
        # 7. Final verification
        print("📍 7. Final verification...")
        cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
        final_total = cursor.fetchone()[0]
        print(f"📊 Final total workers: {final_total}")
        
        cursor.execute("SELECT worker_id FROM worker_cooldowns ORDER BY worker_id")
        final_workers = [row[0] for row in cursor.fetchall()]
        print(f"📋 Final workers: {final_workers}")
        
        conn.close()
        
        if final_total == 10 and final_workers == workers_to_keep:
            print("✅ ROOT PROBLEM FIXED!")
            print("✅ Exactly 10 workers (1-10) now exist in database")
            return True
        else:
            print("❌ Root problem not fully fixed")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing root problem: {e}")
        return False

async def test_worker_functions():
    """Test that worker functions work correctly after fix."""
    try:
        print("\n🧪 Testing worker functions...")
        
        # Import database manager
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.database.manager import DatabaseManager
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Test get_all_workers
        all_workers = await db.get_all_workers()
        print(f"📊 get_all_workers(): {len(all_workers)} workers")
        
        # Test get_available_workers
        available_workers = await db.get_available_workers()
        print(f"📊 get_available_workers(): {len(available_workers)} workers")
        
        if len(all_workers) == 10:
            print("✅ Worker count is now correct!")
            return True
        else:
            print(f"❌ Worker count is still wrong: {len(all_workers)}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing worker functions: {e}")
        return False

def main():
    """Main function."""
    print("🚨 ROOT PROBLEM FIX: Excess Workers")
    print("=" * 60)
    
    # Fix the root problem
    if asyncio.run(fix_worker_count_root()):
        print("\n✅ Root problem fixed successfully!")
        
        # Test worker functions
        if asyncio.run(test_worker_functions()):
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📋 SUMMARY:")
            print("✅ Excess workers deleted")
            print("✅ Exactly 10 workers (1-10) now exist")
            print("✅ Database functions working correctly")
            print("✅ Bot should no longer freeze")
            print("\n🔄 Next steps:")
            print("1. Restart the bot")
            print("2. Test admin interface")
            print("3. Verify no more freezing")
            print("4. Check worker status shows 10 workers")
        else:
            print("\n❌ Worker function tests failed")
    else:
        print("\n❌ Failed to fix root problem")
    
    print("=" * 60)

if __name__ == "__main__":
    import sys
    import os
    main()
