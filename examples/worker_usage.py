#!/usr/bin/env python3
"""
Example usage of WorkerManager for Telegram bot automation.
"""

import asyncio
import logging
import os
from datetime import datetime

# Add src to path
import sys
sys.path.append('src')

from worker_manager import WorkerManager
from src.database.manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Example usage of WorkerManager."""
    
    # Initialize database
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    # Initialize worker manager
    worker_manager = WorkerManager(db_manager, logger)
    
    try:
        # Initialize workers
        await worker_manager.initialize_workers()
        
        # Check worker health
        health = await worker_manager.check_worker_health()
        print(f"Worker Health: {health}")
        
        # Get worker stats
        stats = worker_manager.get_worker_stats()
        print(f"Worker Stats: {stats}")
        
        # Example: Post a message
        chat_id = -1001234567890  # Replace with actual chat ID
        message = "Hello from WorkerManager! 🚀"
        
        success = await worker_manager.post_message(chat_id, message)
        if success:
            print(f"✅ Message posted successfully to {chat_id}")
        else:
            print(f"❌ Failed to post message to {chat_id}")
        
        # Check health again after posting
        health_after = await worker_manager.check_worker_health()
        print(f"Health after posting: {health_after}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        # Close workers
        await worker_manager.close_workers()

if __name__ == "__main__":
    # Set up environment variables for workers
    # You need to set these in your environment or .env file
    os.environ.update({
        'WORKER_1_API_ID': 'your_api_id_1',
        'WORKER_1_API_HASH': 'your_api_hash_1',
        'WORKER_1_PHONE': '+1234567890',
        
        'WORKER_2_API_ID': 'your_api_id_2',
        'WORKER_2_API_HASH': 'your_api_hash_2',
        'WORKER_2_PHONE': '+1234567891',
        
        'WORKER_4_API_ID': 'your_api_id_4',
        'WORKER_4_API_HASH': 'your_api_hash_4',
        'WORKER_4_PHONE': '+1234567893',
    })
    
    asyncio.run(main()) 