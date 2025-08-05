#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('config/.env')

async def quick_worker_check():
    """Quick check of worker status."""
    logger.info("🔍 Quick worker status check...")
    
    # Load workers from environment
    workers = []
    worker_index = 1
    while True:
        api_id = os.getenv(f"WORKER_{worker_index}_API_ID")
        api_hash = os.getenv(f"WORKER_{worker_index}_API_HASH")
        phone = os.getenv(f"WORKER_{worker_index}_PHONE")
        
        if not all([api_id, api_hash, phone]):
            break
        
        workers.append({
            'index': worker_index,
            'api_id': api_id,
            'api_hash': api_hash,
            'phone': phone
        })
        
        worker_index += 1
    
    logger.info(f"Found {len(workers)} workers configured")
    
    # Check session files
    session_files = []
    if os.path.exists('sessions'):
        session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
    
    logger.info(f"Session files: {len(session_files)}")
    
    # Quick connection test for first few workers
    active_workers = []
    failed_workers = []
    
    for i, worker in enumerate(workers[:5]):  # Test first 5 workers
        try:
            session_name = f"sessions/worker_{worker['index']}"
            client = TelegramClient(session_name, int(worker['api_id']), worker['api_hash'])
            
            await client.start(phone=worker['phone'])
            
            if await client.is_user_authorized():
                me = await client.get_me()
                logger.info(f"✅ Worker {worker['index']} ({worker['phone']}): @{me.username}")
                active_workers.append(worker['index'])
            else:
                logger.error(f"❌ Worker {worker['index']} not authorized")
                failed_workers.append(worker['index'])
            
            await client.disconnect()
            
        except Exception as e:
            logger.error(f"❌ Worker {worker['index']} failed: {e}")
            failed_workers.append(worker['index'])
        
        await asyncio.sleep(1)
    
    # Check scheduler logs for recent activity
    logger.info("📊 Checking recent scheduler activity...")
    try:
        with open('logs/scheduler.log', 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-20:]  # Last 20 lines
            
            # Look for worker activity
            worker_activity = {}
            for line in recent_lines:
                if "Worker" in line and ("joined" in line or "sent" in line or "ERROR" in line):
                    logger.info(f"   {line.strip()}")
            
    except Exception as e:
        logger.error(f"Could not read scheduler log: {e}")
    
    # Summary
    logger.info("📋 QUICK WORKER STATUS SUMMARY:")
    logger.info(f"   Total configured: {len(workers)}")
    logger.info(f"   Session files: {len(session_files)}")
    logger.info(f"   Active (tested): {len(active_workers)}")
    logger.info(f"   Failed (tested): {len(failed_workers)}")
    
    if failed_workers:
        logger.warning(f"⚠️ Failed workers: {failed_workers}")
    else:
        logger.info("✅ All tested workers are active!")

if __name__ == "__main__":
    asyncio.run(quick_worker_check()) 