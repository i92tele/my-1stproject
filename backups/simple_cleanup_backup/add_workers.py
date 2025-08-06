#!/usr/bin/env python3
"""
Worker Account Management Script
Helps add and test multiple worker accounts for AutoFarming Pro
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import logging

load_dotenv('config/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self):
        self.workers = []
        self.current_worker_index = 0
        
    def load_workers_from_env(self):
        """Load worker configurations from environment variables."""
        logger.info("🔍 Loading worker configurations...")
        
        for i in range(1, 6):  # Support up to 5 workers
            api_id = os.getenv(f"WORKER_{i}_API_ID")
            api_hash = os.getenv(f"WORKER_{i}_API_HASH")
            phone = os.getenv(f"WORKER_{i}_PHONE")
            
            if api_id and api_hash and phone:
                self.workers.append({
                    'api_id': api_id,
                    'api_hash': api_hash,
                    'phone': phone,
                    'client': None,
                    'index': i,
                    'status': 'pending'
                })
                logger.info(f"✅ Found worker {i}: {phone}")
            else:
                logger.info(f"⚠️ Worker {i} not configured")
        
        logger.info(f"📊 Total workers loaded: {len(self.workers)}")
        return len(self.workers) > 0
    
    async def initialize_workers(self):
        """Initialize all worker accounts."""
        logger.info("🚀 Initializing worker accounts...")
        
        for worker in self.workers:
            try:
                # Create Telethon client for this worker
                worker['client'] = TelegramClient(
                    f'session_worker_{worker["index"]}',
                    worker['api_id'],
                    worker['api_hash']
                )
                
                # Start the client
                await worker['client'].start(phone=worker['phone'])
                
                # Test the connection
                me = await worker['client'].get_me()
                worker['status'] = 'active'
                worker['username'] = me.username or f"worker_{worker['index']}"
                
                logger.info(f"✅ Worker {worker['index']} initialized: @{worker['username']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize worker {worker['index']}: {e}")
                worker['client'] = None
                worker['status'] = 'failed'
    
    async def test_workers(self):
        """Test all worker accounts."""
        logger.info("🧪 Testing worker accounts...")
        
        active_workers = 0
        for worker in self.workers:
            if worker['client'] and worker['status'] == 'active':
                try:
                    # Test sending a message to yourself
                    me = await worker['client'].get_me()
                    logger.info(f"✅ Worker {worker['index']} (@{me.username}) is healthy")
                    active_workers += 1
                except Exception as e:
                    logger.error(f"❌ Worker {worker['index']} test failed: {e}")
                    worker['status'] = 'failed'
            else:
                logger.warning(f"⚠️ Worker {worker['index']} is not available")
        
        logger.info(f"📊 Active workers: {active_workers}/{len(self.workers)}")
        return active_workers
    
    async def get_available_worker(self):
        """Get the next available worker in round-robin fashion."""
        available_workers = [w for w in self.workers if w['client'] and w['status'] == 'active']
        
        if not available_workers:
            return None
        
        # Round-robin selection
        worker = available_workers[self.current_worker_index % len(available_workers)]
        self.current_worker_index += 1
        
        return worker
    
    async def send_test_message(self, destination, message):
        """Send a test message using an available worker."""
        worker = await self.get_available_worker()
        
        if not worker:
            logger.error("❌ No available workers")
            return False
        
        try:
            # Send the test message using this worker
            await worker['client'].send_message(destination, message)
            logger.info(f"✅ Test message sent via worker {worker['index']} (@{worker['username']})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker {worker['index']} failed to send message: {e}")
            return False
    
    def print_worker_status(self):
        """Print status of all workers."""
        logger.info("📊 Worker Status Report:")
        logger.info("=" * 50)
        
        for worker in self.workers:
            status_emoji = "✅" if worker['status'] == 'active' else "❌"
            username = worker.get('username', 'Unknown')
            logger.info(f"{status_emoji} Worker {worker['index']}: {worker['phone']} (@{username}) - {worker['status']}")
        
        active_count = len([w for w in self.workers if w['status'] == 'active'])
        logger.info(f"\n📈 Summary: {active_count}/{len(self.workers)} workers active")
    
    async def close_all_workers(self):
        """Close all worker connections."""
        logger.info("🔒 Closing worker connections...")
        
        for worker in self.workers:
            if worker['client']:
                try:
                    await worker['client'].disconnect()
                    logger.info(f"✅ Worker {worker['index']} disconnected")
                except Exception as e:
                    logger.error(f"❌ Error disconnecting worker {worker['index']}: {e}")

async def main():
    """Main function to test worker management."""
    manager = WorkerManager()
    
    # Load workers from environment
    if not manager.load_workers_from_env():
        logger.error("❌ No workers configured. Please add worker credentials to .env file.")
        return
    
    try:
        # Initialize workers
        await manager.initialize_workers()
        
        # Print status
        manager.print_worker_status()
        
        # Test workers
        active_count = await manager.test_workers()
        
        if active_count > 0:
            logger.info(f"🎉 Successfully initialized {active_count} workers!")
            
            # Optional: Send test message
            # await manager.send_test_message("your_test_channel", "Test message from AutoFarming Pro")
            
        else:
            logger.error("❌ No workers are active. Please check your credentials.")
    
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error in worker management: {e}")
    finally:
        await manager.close_all_workers()

if __name__ == "__main__":
    asyncio.run(main()) 