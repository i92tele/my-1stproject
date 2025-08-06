#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError, UserBannedInChannelError, ChatWriteForbiddenError
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
load_dotenv('config/.env')

class BannedWorkerChecker:
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
        """Test connection and check for bans for a single worker."""
        try:
            session_name = f"sessions/worker_{worker_config['index']}"
            os.makedirs('sessions', exist_ok=True)
            
            client = TelegramClient(session_name, int(worker_config['api_id']), worker_config['api_hash'])
            
            # Start client
            await client.start(phone=worker_config['phone'])
            
            # Check if authorized
            if not await client.is_user_authorized():
                logger.error(f"❌ Worker {worker_config['index']} not authorized")
                await client.disconnect()
                return {'status': 'not_authorized', 'worker': worker_config['index']}
            
            # Get user info
            me = await client.get_me()
            logger.info(f"✅ Worker {worker_config['index']} ({worker_config['phone']}) connected: @{me.username}")
            
            # Test sending a message to self to check for restrictions
            try:
                await client.send_message('me', 'Test message - checking worker status')
                logger.info(f"✅ Worker {worker_config['index']} can send messages")
                message_ok = True
            except Exception as e:
                logger.warning(f"⚠️ Worker {worker_config['index']} has message restrictions: {e}")
                message_ok = False
            
            # Test joining a public group
            test_group = "@test_crypto_group"
            try:
                from telethon.tl.functions.channels import JoinChannelRequest
                await client(JoinChannelRequest(channel=test_group))
                logger.info(f"✅ Worker {worker_config['index']} can join groups")
                join_ok = True
            except Exception as e:
                logger.warning(f"⚠️ Worker {worker_config['index']} has joining restrictions: {e}")
                join_ok = False
            
            await client.disconnect()
            
            return {
                'status': 'active',
                'worker': worker_config['index'],
                'username': me.username,
                'phone': worker_config['phone'],
                'can_send_messages': message_ok,
                'can_join_groups': join_ok
            }
                
        except Exception as e:
            logger.error(f"❌ Failed to connect worker {worker_config['index']}: {e}")
            return {'status': 'failed', 'worker': worker_config['index'], 'error': str(e)}
    
    async def test_worker_in_groups(self, worker_config, test_groups):
        """Test if worker can access specific groups."""
        try:
            session_name = f"sessions/worker_{worker_config['index']}"
            client = TelegramClient(session_name, int(worker_config['api_id']), worker_config['api_hash'])
            
            await client.start(phone=worker_config['phone'])
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return {'status': 'not_authorized', 'worker': worker_config['index']}
            
            group_results = {}
            
            for group in test_groups:
                try:
                    # Try to get group info
                    entity = await client.get_entity(group)
                    logger.info(f"✅ Worker {worker_config['index']} can access {group}")
                    group_results[group] = 'accessible'
                except Exception as e:
                    logger.warning(f"⚠️ Worker {worker_config['index']} cannot access {group}: {e}")
                    group_results[group] = 'banned_or_restricted'
            
            await client.disconnect()
            
            return {
                'status': 'tested',
                'worker': worker_config['index'],
                'group_results': group_results
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to test worker {worker_config['index']} in groups: {e}")
            return {'status': 'failed', 'worker': worker_config['index'], 'error': str(e)}
    
    async def check_all_workers(self):
        """Check all workers for bans and restrictions."""
        logger.info("🔍 Checking all workers for bans and restrictions...")
        
        results = []
        test_groups = ["@test_crypto_group", "@binance_signals", "@cryptosignals"]
        
        for worker in self.workers:
            logger.info(f"Testing worker {worker['index']} ({worker['phone']})...")
            
            # Basic connection test
            result = await self.test_worker_connection(worker)
            results.append(result)
            
            # Group access test
            group_result = await self.test_worker_in_groups(worker, test_groups)
            results.append(group_result)
            
            await asyncio.sleep(2)  # Delay between workers
        
        return results
    
    def analyze_results(self, results):
        """Analyze the results and identify banned/restricted workers."""
        logger.info("📊 Analyzing worker results...")
        
        active_workers = []
        banned_workers = []
        restricted_workers = []
        failed_workers = []
        
        for result in results:
            if result['status'] == 'active':
                if result.get('can_send_messages', True) and result.get('can_join_groups', True):
                    active_workers.append(result)
                else:
                    restricted_workers.append(result)
            elif result['status'] == 'failed':
                failed_workers.append(result)
            elif result['status'] == 'not_authorized':
                failed_workers.append(result)
        
        # Check group access results
        for result in results:
            if result['status'] == 'tested':
                banned_groups = [group for group, status in result.get('group_results', {}).items() 
                               if status == 'banned_or_restricted']
                if banned_groups:
                    logger.warning(f"⚠️ Worker {result['worker']} banned from groups: {banned_groups}")
                    banned_workers.append(result)
        
        logger.info(f"📈 Worker Analysis:")
        logger.info(f"   ✅ Active workers: {len(active_workers)}")
        logger.info(f"   ⚠️ Restricted workers: {len(restricted_workers)}")
        logger.info(f"   ❌ Banned workers: {len(banned_workers)}")
        logger.info(f"   🔧 Failed workers: {len(failed_workers)}")
        
        if banned_workers:
            logger.warning("🚨 BANNED WORKERS DETECTED:")
            for worker in banned_workers:
                logger.warning(f"   Worker {worker['worker']}: {worker.get('error', 'Banned from groups')}")
        
        if restricted_workers:
            logger.warning("⚠️ RESTRICTED WORKERS:")
            for worker in restricted_workers:
                restrictions = []
                if not worker.get('can_send_messages', True):
                    restrictions.append("Cannot send messages")
                if not worker.get('can_join_groups', True):
                    restrictions.append("Cannot join groups")
                logger.warning(f"   Worker {worker['worker']}: {', '.join(restrictions)}")
        
        return {
            'active': active_workers,
            'banned': banned_workers,
            'restricted': restricted_workers,
            'failed': failed_workers
        }

async def main():
    """Run the banned worker check."""
    checker = BannedWorkerChecker()
    
    if not checker.workers:
        logger.error("❌ No workers found in environment configuration")
        return
    
    # Check all workers
    results = await checker.check_all_workers()
    
    # Analyze results
    analysis = checker.analyze_results(results)
    
    # Summary
    logger.info("📋 BANNED WORKER CHECK SUMMARY:")
    logger.info(f"   Total workers: {len(checker.workers)}")
    logger.info(f"   Active: {len(analysis['active'])}")
    logger.info(f"   Banned: {len(analysis['banned'])}")
    logger.info(f"   Restricted: {len(analysis['restricted'])}")
    logger.info(f"   Failed: {len(analysis['failed'])}")
    
    if analysis['banned'] or analysis['restricted']:
        logger.warning("🔧 RECOMMENDATION: Consider replacing banned/restricted workers")
    else:
        logger.info("✅ All workers are healthy!")

if __name__ == "__main__":
    asyncio.run(main()) 