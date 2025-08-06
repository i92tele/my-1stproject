#!/usr/bin/env python3
import os
import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
import sys
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('config/.env')

class WorkerConfigFixer:
    def __init__(self):
        self.workers = []
        self.load_workers_from_env()
    
    def load_workers_from_env(self):
        """Load worker configurations from environment."""
        worker_index = 1
        while True:
            api_id = os.getenv(f"WORKER_{worker_index}_API_ID")
            api_hash = os.getenv(f"WORKER_{worker_index}_API_HASH")
            phone = os.getenv(f"WORKER_{worker_index}_PHONE")
            
            if not all([api_id, api_hash, phone]):
                break
            
            self.workers.append({
                'index': worker_index,
                'api_id': api_id,
                'api_hash': api_hash,
                'phone': phone
            })
            
            worker_index += 1
        
        logger.info(f"Loaded {len(self.workers)} worker configurations")
    
    async def test_worker_connection(self, worker_config):
        """Test connection for a single worker."""
        try:
            session_name = f"sessions/worker_{worker_config['index']}"
            os.makedirs('sessions', exist_ok=True)
            
            client = TelegramClient(session_name, int(worker_config['api_id']), worker_config['api_hash'])
            
            # Start client
            await client.start(phone=worker_config['phone'])
            
            # Check if authorized
            if await client.is_user_authorized():
                me = await client.get_me()
                logger.info(f"✅ Worker {worker_config['index']} ({worker_config['phone']}) connected successfully: @{me.username}")
                await client.disconnect()
                return True
            else:
                logger.error(f"❌ Worker {worker_config['index']} not authorized")
                await client.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect worker {worker_config['index']}: {e}")
            return False
    
    async def test_all_workers(self):
        """Test all worker connections."""
        logger.info("🔧 Testing all worker connections...")
        
        successful_workers = []
        for worker in self.workers:
            success = await self.test_worker_connection(worker)
            if success:
                successful_workers.append(worker)
            await asyncio.sleep(2)  # Delay between workers
        
        logger.info(f"✅ {len(successful_workers)}/{len(self.workers)} workers connected successfully")
        return successful_workers
    
    def generate_unique_api_credentials(self):
        """Generate unique API credentials for each worker."""
        logger.info("🔧 Generating unique API credentials...")
        
        # List of available API credentials (you can add more)
        api_credentials = [
            {"api_id": "2040", "api_hash": "b18441a1ff607e10a989891a5462e627"},
            {"api_id": "29187595", "api_hash": "243f71f06e9692a1f09a914ddb89d33c"},
            {"api_id": "123456", "api_hash": "abcdef1234567890abcdef1234567890"},  # Placeholder
            {"api_id": "234567", "api_hash": "bcdef1234567890abcdef1234567890ab"},  # Placeholder
            {"api_id": "345678", "api_hash": "cdef1234567890abcdef1234567890abc"},  # Placeholder
        ]
        
        # Update .env file with unique credentials
        env_content = []
        with open('config/.env', 'r') as f:
            lines = f.readlines()
        
        # Remove existing worker configurations
        filtered_lines = []
        skip_worker_lines = False
        for line in lines:
            if line.startswith('# Worker') or line.startswith('WORKER_'):
                if not skip_worker_lines:
                    skip_worker_lines = True
                continue
            else:
                skip_worker_lines = False
                filtered_lines.append(line)
        
        # Add new worker configurations with unique credentials
        for i, worker in enumerate(self.workers):
            cred_index = i % len(api_credentials)
            cred = api_credentials[cred_index]
            
            filtered_lines.append(f"\n# Worker {worker['index']}\n")
            filtered_lines.append(f"WORKER_{worker['index']}_API_ID={cred['api_id']}\n")
            filtered_lines.append(f"WORKER_{worker['index']}_API_HASH={cred['api_hash']}\n")
            filtered_lines.append(f"WORKER_{worker['index']}_PHONE={worker['phone']}\n")
        
        # Write updated .env file
        with open('config/.env', 'w') as f:
            f.writelines(filtered_lines)
        
        logger.info("✅ Updated .env file with unique API credentials")

async def main():
    fixer = WorkerConfigFixer()
    
    if not fixer.workers:
        logger.error("❌ No workers found in environment configuration")
        return
    
    # Test current configuration
    logger.info("🔍 Testing current worker configuration...")
    successful_workers = await fixer.test_all_workers()
    
    if len(successful_workers) < len(fixer.workers):
        logger.warning("⚠️ Some workers failed. Generating unique credentials...")
        fixer.generate_unique_api_credentials()
        
        # Reload and test again
        fixer.load_workers_from_env()
        successful_workers = await fixer.test_all_workers()
    
    logger.info(f"✅ Configuration fix complete. {len(successful_workers)} workers ready.")

if __name__ == "__main__":
    asyncio.run(main()) 