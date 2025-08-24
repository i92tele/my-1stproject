#!/usr/bin/env python3
"""
Worker Setup Script for AutoFarming Bot
Authenticates all configured workers and creates session files for persistent login.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config/.env')

class WorkerSetup:
    def __init__(self):
        self.workers = []
        self.load_workers_from_env()
    
    def load_workers_from_env(self):
        """Load worker credentials from environment variables"""
        worker_count = 0
        
        for i in range(1, 11):  # Check workers 1-10
            api_id = os.getenv(f'WORKER_{i}_API_ID')
            api_hash = os.getenv(f'WORKER_{i}_API_HASH')
            phone = os.getenv(f'WORKER_{i}_PHONE')
            
            # Skip if any credential is missing or placeholder
            if not api_id or not api_hash or not phone:
                continue
                
            if (api_id == 'your_worker_2_api_id' or 
                api_id == 'your_worker_3_api_id' or 
                api_id == 'your_worker_5_api_id'):
                continue
            
            try:
                api_id = int(api_id)
                self.workers.append({
                    'worker_id': i,
                    'api_id': api_id,
                    'api_hash': api_hash,
                    'phone': phone
                })
                worker_count += 1
                logger.info(f"Found worker {i}: {phone}")
            except ValueError:
                logger.warning(f"Invalid API_ID for worker {i}: {api_id}")
        
        logger.info(f"Loaded {worker_count} workers from environment")
    
    async def setup_worker(self, worker):
        """Setup authentication for a single worker"""
        worker_id = worker['worker_id']
        api_id = worker['api_id']
        api_hash = worker['api_hash']
        phone = worker['phone']
        
        session_file = f"sessions/worker_{worker_id}"
        
        logger.info(f"Setting up Worker {worker_id} ({phone})...")
        
        client = None
        try:
            # Create client
            client = TelegramClient(session_file, api_id, api_hash)
            
            # Connect first
            await client.connect()
            
            # Check if already authorized
            if await client.is_user_authorized():
                logger.info(f"Worker {worker_id} already authorized!")
                return True
            
            # Send code request
            await client.send_code_request(phone)
            
            # Get code from user
            print(f"\n📱 Worker {worker_id} ({phone})")
            print("=" * 50)
            code = input("Enter the Telegram verification code: ").strip()
            
            try:
                # Sign in with code
                await client.sign_in(phone, code)
                logger.info(f"Worker {worker_id} authenticated successfully!")
                return True
                
            except SessionPasswordNeededError:
                # 2FA enabled
                print(f"\n🔐 Worker {worker_id} has 2FA enabled")
                password = input("Enter your 2FA password: ").strip()
                await client.sign_in(password=password)
                logger.info(f"Worker {worker_id} authenticated with 2FA!")
                return True
                
            except PhoneCodeInvalidError:
                logger.error(f"Invalid code for Worker {worker_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up Worker {worker_id}: {e}")
            return False
        finally:
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
    
    async def setup_all_workers(self):
        """Setup all workers"""
        if not self.workers:
            logger.error("No workers found in environment variables!")
            return
        
        print(f"\n🚀 Setting up {len(self.workers)} workers...")
        print("=" * 60)
        
        # Ensure sessions directory exists
        os.makedirs('sessions', exist_ok=True)
        
        successful = 0
        for worker in self.workers:
            if await self.setup_worker(worker):
                successful += 1
            print()  # Add spacing between workers
        
        print("=" * 60)
        logger.info(f"Setup complete! {successful}/{len(self.workers)} workers authenticated")
        
        if successful == len(self.workers):
            print("✅ All workers ready! You can now start the bot.")
        else:
            print("⚠️  Some workers failed. Check the logs above.")

async def main():
    """Main function"""
    print("🔧 AutoFarming Bot - Worker Setup")
    print("=" * 40)
    
    setup = WorkerSetup()
    await setup.setup_all_workers()

if __name__ == "__main__":
    asyncio.run(main())
