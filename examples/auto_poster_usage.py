#!/usr/bin/env python3
"""
Example usage of AutoPoster for automated ad posting.
"""

import asyncio
import logging
import os
from datetime import datetime

# Add src to path
import sys
sys.path.append('src')

from auto_poster import AutoPoster, initialize_auto_poster
from worker_manager import WorkerManager
from src.database.manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Example usage of AutoPoster."""
    
    # Initialize database
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    # Initialize worker manager
    worker_manager = WorkerManager(db_manager, logger)
    await worker_manager.initialize_workers()
    
    # Initialize AutoPoster
    auto_poster = AutoPoster(db_manager, worker_manager, logger)
    
    try:
        # Example 1: Get status
        status = await auto_poster.get_status()
        print(f"AutoPoster Status: {status}")
        
        # Example 2: Process a single ad slot
        slot_id = 1  # Replace with actual slot ID
        result = await auto_poster.process_single_ad(slot_id)
        print(f"Single Ad Result: {result}")
        
        # Example 3: Start the posting cycle (runs continuously)
        print("Starting AutoPoster cycle...")
        # Uncomment to run the continuous cycle:
        # await auto_poster.start()
        
        # Example 4: Manual posting cycle
        print("Running manual posting cycle...")
        ads_to_post = await auto_poster.get_ads_to_post()
        print(f"Found {len(ads_to_post)} ads to post")
        
        for ad_slot in ads_to_post:
            result = await auto_poster.process_ad_slot(ad_slot)
            print(f"Processed slot {ad_slot['id']}: {result}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        # Stop AutoPoster
        await auto_poster.stop()
        
        # Close workers
        await worker_manager.close_workers()

async def setup_example_data(db_manager):
    """Set up example data for testing."""
    try:
        # Create example user
        await db_manager.create_or_update_user(
            user_id=12345,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        
        # Create example ad slot
        slot_id = await db_manager.create_ad_slot(user_id=12345, slot_number=1)
        if slot_id:
            # Add content to slot
            await db_manager.update_slot_content(
                slot_id=slot_id,
                content="🚀 Test ad content! This is an example advertisement.",
                file_id=None
            )
            
            # Activate the slot
            await db_manager.activate_slot(slot_id)
            
            # Add example destinations
            await db_manager.add_slot_destination(
                slot_id=slot_id,
                dest_type="group",
                dest_id="-1001234567890",
                dest_name="Test Group 1"
            )
            
            await db_manager.add_slot_destination(
                slot_id=slot_id,
                dest_type="group", 
                dest_id="-1001234567891",
                dest_name="Test Group 2"
            )
            
            print(f"✅ Created example ad slot {slot_id}")
        
        # Add example managed groups
        await db_manager.add_managed_group(
            group_id="-1001234567890",
            group_name="Test Group 1",
            category="general"
        )
        
        await db_manager.add_managed_group(
            group_id="-1001234567891", 
            group_name="Test Group 2",
            category="general"
        )
        
        print("✅ Created example data")
        
    except Exception as e:
        logger.error(f"Error setting up example data: {e}")

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