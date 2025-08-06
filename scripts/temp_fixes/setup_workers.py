#!/usr/bin/env python3
"""
Worker Setup Script
Run this once to authenticate workers
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from scheduler.config.worker_config import WorkerConfig
from scheduler.workers.worker_client import WorkerClient

async def setup_worker(worker_creds):
    """Setup a single worker."""
    print(f"\n🔧 Setting up Worker {worker_creds.worker_id}")
    print(f"�� Phone: {worker_creds.phone}")
    
    worker = WorkerClient(
        worker_id=worker_creds.worker_id,
        api_id=worker_creds.api_id,
        api_hash=worker_creds.api_hash,
        phone=worker_creds.phone,
        session_file=worker_creds.session_file
    )
    
    # Create sessions directory if it doesn't exist
    os.makedirs(os.path.dirname(worker_creds.session_file), exist_ok=True)
    
    try:
        # Connect and authenticate
        client = worker.client = TelegramClient(
            worker.session_file, 
            worker.api_id, 
            worker.api_hash
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            print(f"✅ Worker {worker_creds.worker_id}: Already authenticated")
            await client.disconnect()
            return True
            
        # Need to authenticate
        print(f"�� Worker {worker_creds.worker_id}: Sending code to {worker_creds.phone}")
        await client.send_code_request(worker_creds.phone)
        
        # Get code from user
        code = input(f"📱 Enter code for Worker {worker_creds.worker_id}: ")
        
        try:
            await client.sign_in(worker_creds.phone, code)
            print(f"✅ Worker {worker_creds.worker_id}: Authentication successful")
            await client.disconnect()
            return True
        except SessionPasswordNeededError:
            # 2FA required
            password = input(f"�� Enter 2FA password for Worker {worker_creds.worker_id}: ")
            await client.sign_in(password=password)
            print(f"✅ Worker {worker_creds.worker_id}: 2FA authentication successful")
            await client.disconnect()
            return True
            
    except Exception as e:
        print(f"❌ Worker {worker_creds.worker_id}: Setup failed: {e}")
        return False

async def main():
    """Setup all workers."""
    print("🚀 Worker Setup Script")
    print("=" * 50)
    
    # Load worker credentials
    worker_config = WorkerConfig()
    workers = worker_config.load_workers_from_env()
    
    if not workers:
        print("❌ No worker credentials found in environment")
        return
        
    print(f"�� Found {len(workers)} workers to setup")
    
    # Setup each worker
    successful = 0
    for worker_creds in workers:
        if await setup_worker(worker_creds):
            successful += 1
            
    print(f"\n📊 Setup Complete: {successful}/{len(workers)} workers ready")
    
    if successful == len(workers):
        print("✅ All workers are ready! You can now run the scheduler.")
    else:
        print("⚠️ Some workers failed setup. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
