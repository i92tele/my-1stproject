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
        self.target_group = "@roexchangeschat"  # Target group to test
    
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
    
    async def test_worker_in_target_group(self, worker_config):
        """Test if worker can send messages to @roexchangeschat."""
        try:
            session_name = f"sessions/worker_{worker_config['index']}"
            client = TelegramClient(session_name, int(worker_config['api_id']), worker_config['api_hash'])
            
            await client.start(phone=worker_config['phone'])
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return {'status': 'not_authorized', 'worker': worker_config['index']}
            
            # Get user info
            me = await client.get_me()
            
            # Test message to send
            test_message = f"🤖 Worker {worker_config['index']} (@{me.username}) - Testing access to {self.target_group}"
            
            try:
                # Try to send message to target group
                await client.send_message(self.target_group, test_message)
                logger.info(f"✅ Worker {worker_config['index']} (@{me.username}) CAN send messages to {self.target_group}")
                
                await client.disconnect()
                return {
                    'status': 'can_post',
                    'worker': worker_config['index'],
                    'username': me.username,
                    'phone': worker_config['phone'],
                    'target_group': self.target_group
                }
                
            except UserBannedInChannelError:
                logger.error(f"❌ Worker {worker_config['index']} (@{me.username}) is BANNED from {self.target_group}")
                await client.disconnect()
                return {
                    'status': 'banned_from_group',
                    'worker': worker_config['index'],
                    'username': me.username,
                    'phone': worker_config['phone'],
                    'target_group': self.target_group,
                    'error': 'UserBannedInChannelError'
                }
                
            except ChatWriteForbiddenError:
                logger.warning(f"⚠️ Worker {worker_config['index']} (@{me.username}) cannot write to {self.target_group} - group restrictions")
                await client.disconnect()
                return {
                    'status': 'write_forbidden',
                    'worker': worker_config['index'],
                    'username': me.username,
                    'phone': worker_config['phone'],
                    'target_group': self.target_group,
                    'error': 'ChatWriteForbiddenError'
                }
                
            except FloodWaitError as e:
                logger.warning(f"⚠️ Worker {worker_config['index']} (@{me.username}) hit rate limit for {self.target_group}: {e}")
                await client.disconnect()
                return {
                    'status': 'rate_limited',
                    'worker': worker_config['index'],
                    'username': me.username,
                    'phone': worker_config['phone'],
                    'target_group': self.target_group,
                    'error': f'FloodWaitError: {e}'
                }
                
            except Exception as e:
                logger.error(f"❌ Worker {worker_config['index']} (@{me.username}) error with {self.target_group}: {e}")
                await client.disconnect()
                return {
                    'status': 'error',
                    'worker': worker_config['index'],
                    'username': me.username,
                    'phone': worker_config['phone'],
                    'target_group': self.target_group,
                    'error': str(e)
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to test worker {worker_config['index']} in {self.target_group}: {e}")
            return {'status': 'failed', 'worker': worker_config['index'], 'error': str(e)}
    
    async def check_all_workers(self):
        """Check all workers for bans and restrictions."""
        logger.info(f"🔍 Checking all workers for access to {self.target_group}...")
        
        results = []
        
        for worker in self.workers:
            logger.info(f"Testing worker {worker['index']} ({worker['phone']})...")
            
            # Test access to target group
            result = await self.test_worker_in_target_group(worker)
            results.append(result)
            
            await asyncio.sleep(3)  # Delay between workers to avoid rate limits
        
        return results
    
    def analyze_results(self, results):
        """Analyze the results and identify banned/restricted workers."""
        logger.info("📊 Analyzing worker results...")
        
        can_post_workers = []
        banned_workers = []
        restricted_workers = []
        rate_limited_workers = []
        failed_workers = []
        
        for result in results:
            if result['status'] == 'can_post':
                can_post_workers.append(result)
            elif result['status'] == 'banned_from_group':
                banned_workers.append(result)
            elif result['status'] == 'write_forbidden':
                restricted_workers.append(result)
            elif result['status'] == 'rate_limited':
                rate_limited_workers.append(result)
            elif result['status'] in ['failed', 'not_authorized', 'error']:
                failed_workers.append(result)
        
        logger.info(f"📈 Worker Analysis for {self.target_group}:")
        logger.info(f"   ✅ Can post: {len(can_post_workers)}")
        logger.info(f"   ❌ Banned: {len(banned_workers)}")
        logger.info(f"   ⚠️ Restricted: {len(restricted_workers)}")
        logger.info(f"   🕐 Rate limited: {len(rate_limited_workers)}")
        logger.info(f"   🔧 Failed: {len(failed_workers)}")
        
        if banned_workers:
            logger.warning("🚨 BANNED WORKERS FROM TARGET GROUP:")
            for worker in banned_workers:
                logger.warning(f"   Worker {worker['worker']} (@{worker['username']}): {worker['phone']}")
        
        if restricted_workers:
            logger.warning("⚠️ RESTRICTED WORKERS:")
            for worker in restricted_workers:
                logger.warning(f"   Worker {worker['worker']} (@{worker['username']}): {worker['phone']} - {worker['error']}")
        
        if rate_limited_workers:
            logger.warning("🕐 RATE LIMITED WORKERS:")
            for worker in rate_limited_workers:
                logger.warning(f"   Worker {worker['worker']} (@{worker['username']}): {worker['phone']} - {worker['error']}")
        
        return {
            'can_post': can_post_workers,
            'banned': banned_workers,
            'restricted': restricted_workers,
            'rate_limited': rate_limited_workers,
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
    logger.info("📋 TARGET GROUP ACCESS SUMMARY:")
    logger.info(f"   Target group: {checker.target_group}")
    logger.info(f"   Total workers: {len(checker.workers)}")
    logger.info(f"   Can post: {len(analysis['can_post'])}")
    logger.info(f"   Banned: {len(analysis['banned'])}")
    logger.info(f"   Restricted: {len(analysis['restricted'])}")
    logger.info(f"   Rate limited: {len(analysis['rate_limited'])}")
    logger.info(f"   Failed: {len(analysis['failed'])}")
    
    if analysis['banned']:
        logger.warning("🔧 RECOMMENDATION: Replace banned workers")
    elif analysis['can_post']:
        logger.info("✅ Workers ready for posting to target group!")
    else:
        logger.error("❌ No workers can post to target group!")

if __name__ == "__main__":
    asyncio.run(main()) 