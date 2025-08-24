#!/usr/bin/env python3
"""
Fix All Workers Database

This script ensures all 10 workers are properly initialized in the database
"""

import asyncio
import sys
import logging
import sqlite3
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_all_workers_database():
    """Ensure all 10 workers are properly initialized in the database."""
    try:
        print("🔧 Fixing all workers database initialization...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Check current workers in database
        print("📍 1. Checking current workers in database...")
        cursor.execute("SELECT worker_id FROM worker_usage GROUP BY worker_id ORDER BY worker_id")
        existing_workers = [row[0] for row in cursor.fetchall()]
        print(f"📊 Current workers in database: {existing_workers}")
        
        # 2. Initialize all 10 workers
        print("📍 2. Initializing all 10 workers...")
        all_workers = list(range(1, 11))  # Workers 1-10
        missing_workers = [w for w in all_workers if w not in existing_workers]
        
        if missing_workers:
            print(f"📋 Missing workers: {missing_workers}")
            
            for worker_id in missing_workers:
                print(f"🔧 Initializing worker {worker_id}...")
                
                # Initialize in worker_usage table
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_usage 
                    (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, created_at)
                    VALUES (?, 0, 0, 15, 150, CURRENT_TIMESTAMP)
                ''', (worker_id,))
                
                # Initialize in worker_cooldowns table
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_cooldowns 
                    (worker_id, is_active, created_at, updated_at, hourly_limit, daily_limit)
                    VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 15, 150)
                ''', (worker_id,))
                
                print(f"✅ Worker {worker_id} initialized")
        else:
            print("✅ All 10 workers already initialized")
        
        # 3. Verify all workers are now in database
        print("📍 3. Verifying all workers...")
        cursor.execute("SELECT worker_id FROM worker_usage GROUP BY worker_id ORDER BY worker_id")
        all_db_workers = [row[0] for row in cursor.fetchall()]
        print(f"📊 All workers in database: {all_db_workers}")
        
        # 4. Test database manager methods
        print("📍 4. Testing database manager methods...")
        try:
            all_workers_result = await db.get_all_workers()
            available_workers_result = await db.get_available_workers()
            
            print(f"📊 get_all_workers(): {len(all_workers_result)} workers")
            print(f"📊 get_available_workers(): {len(available_workers_result)} workers")
            
            if available_workers_result:
                print("📋 Available workers:")
                for worker in available_workers_result:
                    worker_id = worker.get('worker_id')
                    hourly_posts = worker.get('hourly_posts', 0)
                    daily_posts = worker.get('daily_posts', 0)
                    print(f"  • Worker {worker_id}: {hourly_posts}/15 h, {daily_posts}/150 d")
            else:
                print("❌ No available workers found")
                
        except Exception as e:
            print(f"❌ Error testing database manager: {e}")
        
        # 5. Check worker limits and reset if needed
        print("📍 5. Checking worker limits...")
        cursor.execute('''
            SELECT worker_id, hourly_posts, daily_posts, last_reset 
            FROM worker_usage 
            WHERE worker_id IN (1,2,3,4,5,6,7,8,9,10)
            ORDER BY worker_id
        ''')
        worker_limits = cursor.fetchall()
        
        for worker_id, hourly_posts, daily_posts, last_reset in worker_limits:
            print(f"  • Worker {worker_id}: {hourly_posts}/15 h, {daily_posts}/150 d (reset: {last_reset})")
            
            # Reset limits if they're too high (indicating old data)
            if hourly_posts > 15 or daily_posts > 150:
                print(f"    🔄 Resetting limits for worker {worker_id}")
                cursor.execute('''
                    UPDATE worker_usage 
                    SET hourly_posts = 0, daily_posts = 0, last_reset = CURRENT_TIMESTAMP
                    WHERE worker_id = ?
                ''', (worker_id,))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n✅ All workers database fix completed!")
        print("🔄 Restart your bot to apply the changes")
        print("📊 Expected result: All 10 workers should now be available for parallel posting")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing workers database: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ALL WORKERS DATABASE FIX")
    print("=" * 80)
    
    success = asyncio.run(fix_all_workers_database())
    
    if success:
        print("\n✅ All workers database fix completed successfully!")
    else:
        print("\n❌ All workers database fix failed!")
    
    sys.exit(0 if success else 1)
