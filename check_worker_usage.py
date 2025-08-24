#!/usr/bin/env python3
"""
Check Worker Usage

This script checks why only 1 worker is being used
"""

import asyncio
import sys
import logging
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_worker_usage():
    """Check worker usage and availability."""
    try:
        print("🔍 Checking worker usage and availability...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # 1. Check all workers
        print("\n📍 1. Checking all workers...")
        try:
            all_workers = await db.get_all_workers()
            print(f"📊 Total workers in database: {len(all_workers)}")
            
            if all_workers:
                print("📋 All workers:")
                for worker in all_workers:
                    worker_id = worker.get('worker_id')
                    hourly_posts = worker.get('hourly_posts', 0)
                    daily_posts = worker.get('daily_posts', 0)
                    hourly_limit = worker.get('hourly_limit', 15)
                    daily_limit = worker.get('daily_limit', 150)
                    print(f"  • Worker {worker_id}: {hourly_posts}/{hourly_limit} h, {daily_posts}/{daily_limit} d")
            else:
                print("❌ No workers found in database!")
        except Exception as e:
            print(f"❌ Error getting all workers: {e}")
        
        # 2. Check available workers
        print("\n📍 2. Checking available workers...")
        try:
            available_workers = await db.get_available_workers()
            print(f"📊 Available workers: {len(available_workers)}")
            
            if available_workers:
                print("📋 Available workers:")
                for worker in available_workers:
                    worker_id = worker.get('worker_id')
                    hourly_posts = worker.get('hourly_posts', 0)
                    daily_posts = worker.get('daily_posts', 0)
                    hourly_limit = worker.get('hourly_limit', 15)
                    daily_limit = worker.get('daily_limit', 150)
                    hourly_usage = (hourly_posts / hourly_limit) * 100 if hourly_limit > 0 else 0
                    daily_usage = (daily_posts / daily_limit) * 100 if daily_limit > 0 else 0
                    print(f"  • Worker {worker_id}: {hourly_posts}/{hourly_limit} h ({hourly_usage:.1f}%), {daily_posts}/{daily_limit} d ({daily_usage:.1f}%)")
            else:
                print("❌ No available workers!")
        except Exception as e:
            print(f"❌ Error getting available workers: {e}")
        
        # 3. Check worker usage table
        print("\n📍 3. Checking worker_usage table...")
        try:
            import sqlite3
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM worker_usage ORDER BY worker_id")
            usage_records = cursor.fetchall()
            
            if usage_records:
                print(f"📊 Worker usage records: {len(usage_records)}")
                for record in usage_records:
                    print(f"  • Record: {record}")
            else:
                print("📊 No worker usage records found")
            
            conn.close()
        except Exception as e:
            print(f"❌ Error checking worker_usage table: {e}")
        
        # 4. Check worker cooldowns
        print("\n📍 4. Checking worker_cooldowns table...")
        try:
            import sqlite3
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM worker_cooldowns ORDER BY worker_id")
            cooldown_records = cursor.fetchall()
            
            if cooldown_records:
                print(f"📊 Worker cooldown records: {len(cooldown_records)}")
                for record in cooldown_records:
                    print(f"  • Record: {record}")
            else:
                print("📊 No worker cooldown records found")
            
            conn.close()
        except Exception as e:
            print(f"❌ Error checking worker_cooldowns table: {e}")
        
        # 5. Test worker assignment logic
        print("\n📍 5. Testing worker assignment logic...")
        try:
            from scheduler.workers.worker_assignment import WorkerAssignmentService
            assignment_service = WorkerAssignmentService(db)
            
            best_worker = await assignment_service.get_best_available_worker()
            if best_worker:
                worker_id = best_worker.get('worker_id')
                hourly_posts = best_worker.get('hourly_posts', 0)
                daily_posts = best_worker.get('daily_posts', 0)
                print(f"✅ Best available worker: {worker_id} ({hourly_posts} h, {daily_posts} d)")
            else:
                print("❌ No best available worker found")
        except Exception as e:
            print(f"❌ Error testing worker assignment: {e}")
        
        # 6. Check recent posting activity
        print("\n📍 6. Checking recent posting activity...")
        try:
            import sqlite3
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT worker_id, COUNT(*) as post_count, MAX(created_at) as last_post
                FROM worker_usage 
                WHERE created_at >= datetime('now', '-1 hour')
                GROUP BY worker_id
                ORDER BY post_count DESC
            ''')
            recent_activity = cursor.fetchall()
            
            if recent_activity:
                print("📊 Recent posting activity (last hour):")
                for worker_id, post_count, last_post in recent_activity:
                    print(f"  • Worker {worker_id}: {post_count} posts, last: {last_post}")
            else:
                print("📊 No recent posting activity found")
            
            conn.close()
        except Exception as e:
            print(f"❌ Error checking recent activity: {e}")
        
        # Summary
        print("\n📊 SUMMARY:")
        print("-" * 40)
        if len(available_workers) == 1:
            print("🚨 ISSUE: Only 1 worker available")
            print("   This explains why only 1 worker is posting")
            print("   Other workers may be at their limits or have issues")
        elif len(available_workers) == 0:
            print("🚨 ISSUE: No workers available")
            print("   All workers are at their limits or have issues")
        else:
            print(f"✅ {len(available_workers)} workers available")
            print("   The issue might be in the posting logic")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking worker usage: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("WORKER USAGE CHECK")
    print("=" * 80)
    
    success = asyncio.run(check_worker_usage())
    
    if success:
        print("\n✅ Worker usage check completed successfully!")
    else:
        print("\n❌ Worker usage check failed!")
    
    sys.exit(0 if success else 1)
