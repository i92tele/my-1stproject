#!/usr/bin/env python3
"""
Example usage of PostingService for automated ad posting.
"""

import asyncio
import logging
import os
from datetime import datetime

# Add src to path
import sys
sys.path.append('src')

from posting_service import PostingService, initialize_posting_service, start_posting_service_background
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Example usage of PostingService."""
    
    # Initialize database
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    # Initialize posting service
    posting_service = initialize_posting_service(db_manager, logger)
    
    try:
        # Initialize the service
        if await posting_service.initialize():
            print("✅ PostingService initialized successfully")
            
            # Get service status
            status = await posting_service.get_service_status()
            print(f"Service Status: {status['service_status']['is_running']}")
            
            # Start the service as background task
            service_task = await start_posting_service_background()
            print("✅ PostingService started as background task")
            
            # Let it run for a while
            print("🔄 Service is running... Press Ctrl+C to stop")
            await asyncio.sleep(300)  # Run for 5 minutes
            
            # Get status again
            status = await posting_service.get_service_status()
            print(f"Final Status: {status}")
            
        else:
            print("❌ Failed to initialize PostingService")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping service...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Stop the service
        if posting_service:
            await posting_service.stop_service()
            print("✅ PostingService stopped")

async def test_service_controls():
    """Test service control functions."""
    
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    posting_service = initialize_posting_service(db_manager, logger)
    
    try:
        if await posting_service.initialize():
            print("✅ Service initialized")
            
            # Test configuration update
            posting_service.update_config(
                posting_cycle_interval=30,  # 30 minutes
                anti_ban_delay_min=45,     # 45 seconds
                anti_ban_delay_max=90      # 90 seconds
            )
            print("✅ Configuration updated")
            
            # Test status monitoring
            status = await posting_service.get_service_status()
            print(f"Service Status: {status['service_status']}")
            print(f"Statistics: {status['statistics']}")
            print(f"Components: {status['components']}")
            
            # Test manual posting cycle
            print("🔄 Running manual posting cycle...")
            await posting_service.run_posting_cycle()
            
            # Test cleanup
            print("🧹 Running cleanup...")
            await posting_service.cleanup_expired_subscriptions()
            
        else:
            print("❌ Failed to initialize service")
            
    except Exception as e:
        logger.error(f"Error in test: {e}")
    finally:
        if posting_service:
            await posting_service.stop_service()

if __name__ == "__main__":
    # Set up environment variables for workers
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
    
    # Run examples
    print("🚀 Starting PostingService examples...")
    
    # Uncomment to run the main example
    # asyncio.run(main())
    
    # Uncomment to run the control test
    # asyncio.run(test_service_controls())
    
    print("✅ Examples completed") 