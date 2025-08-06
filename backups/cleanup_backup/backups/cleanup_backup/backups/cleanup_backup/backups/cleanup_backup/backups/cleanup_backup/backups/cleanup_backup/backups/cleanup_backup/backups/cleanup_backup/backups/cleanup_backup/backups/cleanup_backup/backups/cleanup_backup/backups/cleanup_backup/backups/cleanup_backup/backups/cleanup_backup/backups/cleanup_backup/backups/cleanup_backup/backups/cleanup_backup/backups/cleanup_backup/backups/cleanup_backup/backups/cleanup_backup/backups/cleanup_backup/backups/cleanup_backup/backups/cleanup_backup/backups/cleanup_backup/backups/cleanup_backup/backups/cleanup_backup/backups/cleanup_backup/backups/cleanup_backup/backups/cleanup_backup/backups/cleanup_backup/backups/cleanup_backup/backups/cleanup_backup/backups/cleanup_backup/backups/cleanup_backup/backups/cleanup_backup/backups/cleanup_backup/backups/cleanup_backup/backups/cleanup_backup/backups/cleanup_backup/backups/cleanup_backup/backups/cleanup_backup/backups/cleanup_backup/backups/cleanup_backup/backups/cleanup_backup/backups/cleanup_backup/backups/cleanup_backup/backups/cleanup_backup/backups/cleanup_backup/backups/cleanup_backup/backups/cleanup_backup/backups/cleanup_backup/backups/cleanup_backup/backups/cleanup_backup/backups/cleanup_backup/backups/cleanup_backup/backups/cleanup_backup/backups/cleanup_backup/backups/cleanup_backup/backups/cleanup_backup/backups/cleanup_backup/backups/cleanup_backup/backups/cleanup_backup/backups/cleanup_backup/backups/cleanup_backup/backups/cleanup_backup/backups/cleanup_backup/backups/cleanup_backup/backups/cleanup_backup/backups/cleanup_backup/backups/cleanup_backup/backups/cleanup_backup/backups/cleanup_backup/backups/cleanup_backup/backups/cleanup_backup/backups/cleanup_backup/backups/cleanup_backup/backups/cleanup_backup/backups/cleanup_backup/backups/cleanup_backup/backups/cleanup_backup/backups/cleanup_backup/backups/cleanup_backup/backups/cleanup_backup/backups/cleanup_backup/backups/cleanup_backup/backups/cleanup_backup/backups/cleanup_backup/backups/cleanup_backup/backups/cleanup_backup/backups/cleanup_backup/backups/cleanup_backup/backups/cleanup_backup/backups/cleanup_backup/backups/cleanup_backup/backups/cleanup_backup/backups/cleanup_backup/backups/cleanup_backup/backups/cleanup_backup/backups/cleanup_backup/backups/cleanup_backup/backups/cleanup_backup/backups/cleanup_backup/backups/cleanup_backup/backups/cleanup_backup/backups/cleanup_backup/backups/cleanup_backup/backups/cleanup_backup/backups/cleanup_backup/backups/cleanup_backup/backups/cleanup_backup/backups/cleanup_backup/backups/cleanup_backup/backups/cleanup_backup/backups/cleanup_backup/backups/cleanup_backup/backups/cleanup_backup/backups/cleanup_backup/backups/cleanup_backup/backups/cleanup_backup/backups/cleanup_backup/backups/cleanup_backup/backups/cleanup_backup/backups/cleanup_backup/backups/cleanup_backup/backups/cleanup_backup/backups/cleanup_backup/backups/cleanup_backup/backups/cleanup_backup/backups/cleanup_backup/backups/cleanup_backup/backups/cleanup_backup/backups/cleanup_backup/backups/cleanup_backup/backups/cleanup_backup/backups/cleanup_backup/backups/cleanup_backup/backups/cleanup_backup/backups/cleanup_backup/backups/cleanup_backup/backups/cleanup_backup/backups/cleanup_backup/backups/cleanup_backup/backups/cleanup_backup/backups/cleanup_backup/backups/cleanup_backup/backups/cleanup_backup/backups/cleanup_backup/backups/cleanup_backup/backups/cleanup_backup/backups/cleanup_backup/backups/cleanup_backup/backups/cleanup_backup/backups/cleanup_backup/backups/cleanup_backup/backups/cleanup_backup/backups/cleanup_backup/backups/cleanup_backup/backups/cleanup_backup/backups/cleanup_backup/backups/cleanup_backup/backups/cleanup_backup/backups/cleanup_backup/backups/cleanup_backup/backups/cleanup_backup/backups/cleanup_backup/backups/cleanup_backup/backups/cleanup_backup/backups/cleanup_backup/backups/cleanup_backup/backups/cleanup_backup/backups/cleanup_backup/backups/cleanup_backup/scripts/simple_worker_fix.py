#!/usr/bin/env python3
import os
import asyncio
import logging
from telethon import TelegramClient
import sys
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('config/.env')

async def test_single_worker(worker_index, api_id, api_hash, phone):
    """Test a single worker connection."""
    try:
        session_name = f"sessions/worker_{worker_index}"
        os.makedirs('sessions', exist_ok=True)
        
        client = TelegramClient(session_name, int(api_id), api_hash)
        
        # Start client
        await client.start(phone=phone)
        
        # Check if authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f"✅ Worker {worker_index} ({phone}) connected: @{me.username}")
            await client.disconnect()
            return True
        else:
            logger.error(f"❌ Worker {worker_index} not authorized")
            await client.disconnect()
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to connect worker {worker_index}: {e}")
        return False

async def main():
    """Test workers with different API credentials."""
    
    # Test with the first API credentials
    logger.info("🔧 Testing workers with first API credentials...")
    
    workers = [
        (1, "+447386300812"),
        (2, "+13018746514"),
        (3, "+12534997118"),
        (4, "+573235112918"),
        (5, "+13015392356"),
        (8, "+13015177101"),
        (9, "+15307729095"),
        (10, "+15405185755"),
        (11, "+15409063048"),
        (12, "+15312357983"),
        (13, "+15153557442"),
        (14, "+15029084987"),
        (15, "+15302872752"),
    ]
    
    # Use the working API credentials
    api_id = "29187595"
    api_hash = "243f71f06e9692a1f09a914ddb89d33c"
    
    successful_workers = []
    
    for worker_index, phone in workers:
        logger.info(f"Testing worker {worker_index} ({phone})...")
        success = await test_single_worker(worker_index, api_id, api_hash, phone)
        if success:
            successful_workers.append((worker_index, phone))
        await asyncio.sleep(3)  # Delay between workers
    
    logger.info(f"✅ {len(successful_workers)}/{len(workers)} workers connected successfully")
    
    # Update .env file with working configuration
    if successful_workers:
        logger.info("🔧 Updating .env file with working configuration...")
        
        # Read current .env file
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
        
        # Add working worker configurations
        for worker_index, phone in successful_workers:
            filtered_lines.append(f"\n# Worker {worker_index}\n")
            filtered_lines.append(f"WORKER_{worker_index}_API_ID={api_id}\n")
            filtered_lines.append(f"WORKER_{worker_index}_API_HASH={api_hash}\n")
            filtered_lines.append(f"WORKER_{worker_index}_PHONE={phone}\n")
        
        # Write updated .env file
        with open('config/.env', 'w') as f:
            f.writelines(filtered_lines)
        
        logger.info(f"✅ Updated .env file with {len(successful_workers)} working workers")

if __name__ == "__main__":
    asyncio.run(main()) 