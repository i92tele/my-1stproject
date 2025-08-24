#!/usr/bin/env python3
"""
Initialize All Workers

This script initializes all 10 workers in the database using the fixed
initialize_worker_limits method.
"""

import asyncio
import sys
import logging
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def initialize_all_workers():
    """Initialize all 10 workers in the database."""
    try:
        print("🔧 Initializing all 10 workers...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Initialize workers 1-10
        worker_ids = list(range(1, 11))  # 1, 2, 3, ..., 10
        successful_initializations = 0
        
        for worker_id in worker_ids:
            print(f"📍 Initializing worker {worker_id}...")
            success = await db.initialize_worker_limits(worker_id)
            if success:
                print(f"✅ Worker {worker_id} initialized successfully")
                successful_initializations += 1
            else:
                print(f"❌ Failed to initialize worker {worker_id}")
        
        print(f"\n📊 Initialization Summary:")
        print(f"✅ Successfully initialized: {successful_initializations}/10 workers")
        
        if successful_initializations == 10:
            print("🎉 All workers initialized successfully!")
            
            # Verify the initialization
            print("\n🔍 Verifying worker initialization...")
            available_workers = await db.get_available_workers()
            print(f"📊 Available workers in database: {len(available_workers)}")
            
            for worker in available_workers:
                worker_id = worker['worker_id']
                hourly_usage = worker['hourly_usage']
                daily_usage = worker['daily_usage']
                hourly_limit = worker['hourly_limit']
                daily_limit = worker['daily_limit']
                print(f"  • Worker {worker_id}: {hourly_usage}/{hourly_limit} h, {daily_usage}/{daily_limit} d")
            
            return True
        else:
            print(f"⚠️ Only {successful_initializations}/10 workers initialized")
            return False
        
    except Exception as e:
        print(f"❌ Error initializing workers: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("WORKER INITIALIZATION")
    print("=" * 80)
    
    success = asyncio.run(initialize_all_workers())
    
    if success:
        print("\n✅ All workers initialized successfully!")
        print("🔄 Restart your bot to use all 10 workers")
        print("📊 Expected result: Parallel posting with all 10 workers")
    else:
        print("\n❌ Worker initialization failed!")
    
    sys.exit(0 if success else 1)
