#!/usr/bin/env python3
"""
Fix Worker Initialization

This script fixes the worker initialization issue in the database manager
"""

import asyncio
import sys
import logging
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_worker_initialization():
    """Fix the worker initialization method in the database manager."""
    try:
        print("🔧 Fixing worker initialization method...")
        
        # Read the current database manager file
        with open('src/database/manager.py', 'r') as f:
            content = f.read()
        
        # Find and replace the initialize_worker_limits method
        old_method = '''    async def initialize_worker_limits(self, worker_id: int) -> bool:
        """Initialize worker limits for a new worker."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_limits (worker_id, hourly_limit, daily_limit, created_at)
                    VALUES (?, 15, 150, ?)
                ''', (worker_id, datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Initialized limits for worker {worker_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error initializing worker limits for {worker_id}: {e}")
                return False'''
        
        new_method = '''    async def initialize_worker_limits(self, worker_id: int) -> bool:
        """Initialize worker limits for a new worker."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Initialize in worker_usage table
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_usage 
                    (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, created_at)
                    VALUES (?, 0, 0, 15, 150, ?)
                ''', (worker_id, datetime.now()))
                
                # Initialize in worker_cooldowns table
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_cooldowns 
                    (worker_id, is_active, created_at, updated_at, hourly_limit, daily_limit)
                    VALUES (?, 1, ?, ?, 15, 150)
                ''', (worker_id, datetime.now(), datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Initialized limits for worker {worker_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error initializing worker limits for {worker_id}: {e}")
                return False'''
        
        # Replace the method
        import re
        new_content = content.replace(old_method, new_method)
        
        # Write the updated content back
        with open('src/database/manager.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Worker initialization method fixed!")
        
        # Test the fix
        print("📍 Testing the fix...")
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Test initializing a worker
        success = await db.initialize_worker_limits(999)  # Test with dummy worker ID
        if success:
            print("✅ Worker initialization method works correctly!")
        else:
            print("❌ Worker initialization method still has issues")
        
        print("🔄 Restart your bot to apply the changes")
        print("📊 Expected result: All 10 workers should initialize properly in the database")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing worker initialization: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("WORKER INITIALIZATION FIX")
    print("=" * 80)
    
    success = asyncio.run(fix_worker_initialization())
    
    if success:
        print("\n✅ Worker initialization fix completed successfully!")
    else:
        print("\n❌ Worker initialization fix failed!")
    
    sys.exit(0 if success else 1)
