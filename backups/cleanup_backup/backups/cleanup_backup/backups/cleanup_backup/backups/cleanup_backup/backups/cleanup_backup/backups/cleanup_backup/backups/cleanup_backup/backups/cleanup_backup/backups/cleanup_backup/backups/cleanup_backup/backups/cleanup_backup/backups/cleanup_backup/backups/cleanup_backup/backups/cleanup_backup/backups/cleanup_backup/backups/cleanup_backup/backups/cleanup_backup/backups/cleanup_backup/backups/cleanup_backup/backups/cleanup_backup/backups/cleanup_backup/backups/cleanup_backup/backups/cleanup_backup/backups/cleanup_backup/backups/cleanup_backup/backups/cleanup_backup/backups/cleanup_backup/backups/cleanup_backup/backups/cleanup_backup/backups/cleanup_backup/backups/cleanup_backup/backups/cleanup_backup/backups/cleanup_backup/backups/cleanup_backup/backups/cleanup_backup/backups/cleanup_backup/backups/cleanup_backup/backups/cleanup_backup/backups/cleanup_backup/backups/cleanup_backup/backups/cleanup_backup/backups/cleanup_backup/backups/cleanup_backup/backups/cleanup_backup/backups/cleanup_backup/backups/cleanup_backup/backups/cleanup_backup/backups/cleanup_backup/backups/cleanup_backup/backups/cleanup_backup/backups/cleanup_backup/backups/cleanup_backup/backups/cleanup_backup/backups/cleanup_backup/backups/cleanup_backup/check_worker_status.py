#!/usr/bin/env python3
"""
Check Worker Status Script
Identifies banned/frozen workers and their status
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import logging

load_dotenv('config/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_worker_status(worker_index):
    """Check if a worker is banned, frozen, or working."""
    try:
        api_id = os.getenv(f'WORKER_{worker_index}_API_ID')
        api_hash = os.getenv(f'WORKER_{worker_index}_API_HASH')
        phone = os.getenv(f'WORKER_{worker_index}_PHONE')
        
        if not all([api_id, api_hash, phone]):
            return {'status': 'not_configured', 'error': 'Missing credentials'}
        
        # Create client
        client = TelegramClient(f'session_worker_{worker_index}', api_id, api_hash)
        
        # Start client
        await client.start(phone=phone)
        
        # Check if authorized
        if not await client.is_user_authorized():
            await client.disconnect()
            return {'status': 'not_authorized', 'error': 'Not authorized'}
        
        # Get user info
        me = await client.get_me()
        
        # Check for restrictions
        try:
            # Try to get account info
            account = await client.get_account()
            
            # Check for restrictions
            restrictions = []
            if hasattr(account, 'restricted') and account.restricted:
                restrictions.append('restricted')
            if hasattr(account, 'deleted') and account.deleted:
                restrictions.append('deleted')
            if hasattr(account, 'bot') and account.bot:
                restrictions.append('bot')
            
            await client.disconnect()
            
            if restrictions:
                return {
                    'status': 'banned/frozen',
                    'restrictions': restrictions,
                    'username': me.username,
                    'phone': phone
                }
            else:
                return {
                    'status': 'working',
                    'username': me.username,
                    'phone': phone
                }
                
        except Exception as e:
            await client.disconnect()
            return {'status': 'error', 'error': str(e), 'phone': phone}
            
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

async def main():
    """Check all workers and identify banned/frozen ones."""
    print("🔍 Checking worker status...")
    print("=" * 50)
    
    banned_workers = []
    working_workers = []
    error_workers = []
    
    for i in range(1, 16):
        print(f"Checking worker {i}...", end=" ")
        result = await check_worker_status(i)
        
        if result['status'] == 'working':
            print(f"✅ Working (@{result.get('username', 'unknown')})")
            working_workers.append(i)
        elif result['status'] == 'banned/frozen':
            print(f"❌ Banned/Frozen ({', '.join(result['restrictions'])})")
            banned_workers.append(i)
        else:
            print(f"⚠️ {result['status']} - {result.get('error', 'Unknown error')}")
            error_workers.append(i)
        
        await asyncio.sleep(1)  # Small delay between checks
    
    print("\n📊 Summary:")
    print("=" * 30)
    print(f"✅ Working workers: {len(working_workers)} ({working_workers})")
    print(f"❌ Banned/Frozen workers: {len(banned_workers)} ({banned_workers})")
    print(f"⚠️ Error workers: {len(error_workers)} ({error_workers})")
    
    if banned_workers:
        print(f"\n🗑️ Workers to remove: {banned_workers}")
        return banned_workers
    else:
        print("\n✅ No banned workers found!")
        return []

if __name__ == "__main__":
    banned_workers = asyncio.run(main()) 