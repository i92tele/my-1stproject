#!/usr/bin/env python3
"""
Ad Scheduler for AutoFarming Pro
Manages automated ad posting with worker rotation
"""

import os
import asyncio
import random
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantRequest
from telethon.errors import InviteRequestSentError, UserPrivacyRestrictedError
from config import BotConfig
from database import DatabaseManager
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdScheduler:
    def __init__(self):
        # Worker rotation to prevent overuse
        self.worker_usage = {}
        self.max_uses_per_hour = 10  # Limit each worker to 10 uses per hour
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager("bot_database.db", logger)
        self.worker_clients = []
        self.current_worker_index = 0
        
    async def initialize(self):
        """Initialize database and worker accounts."""
        await self.db.initialize()
        
        # Load worker accounts from environment
        # Format: WORKER_1_API_ID, WORKER_1_API_HASH, WORKER_1_PHONE
        #         WORKER_2_API_ID, WORKER_2_API_HASH, WORKER_2_PHONE
        worker_index = 1
        while True:
            api_id = os.getenv(f"WORKER_{worker_index}_API_ID")
            api_hash = os.getenv(f"WORKER_{worker_index}_API_HASH")
            phone = os.getenv(f"WORKER_{worker_index}_PHONE")
            
            if not all([api_id, api_hash, phone]):
                break
                
            try:
                session_name = f"sessions/worker_{worker_index}"
                os.makedirs('sessions', exist_ok=True)
                
                client = TelegramClient(session_name, int(api_id), api_hash)
                await client.start(phone=phone)
                
                # Test if client is authorized
                if await client.is_user_authorized():
                    self.worker_clients.append(client)
                    logger.info(f"✅ Worker account {worker_index} connected successfully")
                else:
                    logger.error(f"❌ Worker account {worker_index} not authorized")
                    
            except Exception as e:
                logger.error(f"❌ Failed to connect worker account {worker_index}: {e}")
            
            worker_index += 1
        
        if not self.worker_clients:
            logger.error("❌ No worker accounts available. Please add worker credentials to .env")
            raise Exception("No worker accounts available")
        
        logger.info(f"✅ {len(self.worker_clients)} worker accounts loaded")
    
    def get_next_worker(self):
        """Get the next worker client in rotation."""
        if not self.worker_clients:
            return None
        
        client = self.worker_clients[self.current_worker_index]
        self.current_worker_index = (self.current_worker_index + 1) % len(self.worker_clients)
        return client
    
    async def join_group_with_worker(self, worker_client, group_username: str) -> bool:
        """Join a group using a worker account."""
        try:
            # Try to join the group
            await worker_client(JoinChannelRequest(
                channel=group_username
            ))
            logger.info(f"✅ Worker joined group: {group_username}")
            return True
            
        except InviteRequestSentError:
            logger.info(f"📝 Join request sent for: {group_username}")
            return True
        except UserPrivacyRestrictedError:
            logger.warning(f"�� Cannot join {group_username} due to privacy settings")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to join {group_username}: {e}")
            return False
    
    async def ensure_worker_in_group(self, worker_client, group_username: str) -> bool:
        """Ensure a worker account is in the specified group."""
        try:
            # Check if already in group
            try:
                entity = await worker_client.get_entity(group_username)
                participant = await worker_client(GetParticipantRequest(
                    channel=entity,
                    participant=await worker_client.get_me()
                ))
                logger.info(f"✅ Worker already in group: {group_username}")
                return True
            except:
                # Not in group, try to join
                return await self.join_group_with_worker(worker_client, group_username)
                
        except Exception as e:
            logger.error(f"❌ Error checking/joining group {group_username}: {e}")
            return False
    
    async def send_ad_with_worker(self, worker_client, group_username: str, message: str) -> bool:
        """Send an ad message using a worker account."""
        try:
            # Ensure worker is in the group
            if not await self.ensure_worker_in_group(worker_client, group_username):
                return False
            
            # Send the message
            entity = await worker_client.get_entity(group_username)
            await worker_client.send_message(entity, message)
            
            logger.info(f"✅ Ad sent to {group_username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send ad to {group_username}: {e}")
            return False
    
    async def post_scheduled_ads(self):
        """Post scheduled ads to all managed groups."""
        try:
            # Get all active ad slots
            ad_slots = await self.db.get_active_ad_slots()
            
            if not ad_slots:
                logger.info("📭 No active ad slots found")
                return
            
            # Get managed groups
            managed_groups = await self.db.get_managed_groups()
            
            if not managed_groups:
                logger.warning("⚠️ No managed groups found")
                return
            
            logger.info(f"📤 Posting {len(ad_slots)} ads to {len(managed_groups)} groups")
            
            for ad_slot in ad_slots:
                # Get destinations for this ad slot
                destinations = await self.db.get_destinations_for_slot(ad_slot['id'])
                
                if not destinations:
                    logger.warning(f"⚠️ No destinations found for ad slot {ad_slot['id']}")
                    # Try to set default destinations if none exist
                    await self._set_default_destinations(ad_slot['id'], managed_groups)
                    continue
                
                # Get worker for this ad
                worker_client = self.get_next_worker()
                if not worker_client:
                    logger.error("❌ No worker available")
                    continue
                
                # Post to each destination
                for destination in destinations:
                    try:
                        success = await self.send_ad_with_worker(
                            worker_client, 
                            destination, 
                            ad_slot['ad_content']
                        )
                        
                        if success:
                            # Log the post
                            await self.db.log_ad_post(
                                ad_slot['id'],
                                destination,
                                'success'
                            )
                        
                        # Anti-spam delay
                        await asyncio.sleep(random.randint(30, 60))
                        
                    except Exception as e:
                        logger.error(f"❌ Error posting to {destination}: {e}")
                        await self.db.log_ad_post(
                            ad_slot['id'],
                            destination,
                            'failed'
                        )
            
            logger.info("✅ Ad posting cycle completed")
            
        except Exception as e:
            logger.error(f"❌ Error in post_scheduled_ads: {e}")
    
    async def _set_default_destinations(self, slot_id: int, managed_groups: List[Dict]):
        """Set default destinations for an ad slot if none exist."""
        try:
            # Get first 3 managed groups as default destinations
            default_destinations = [group['group_name'] for group in managed_groups[:3]]
            
            if default_destinations:
                await self.db.update_destinations_for_slot(slot_id, default_destinations)
                logger.info(f"✅ Set default destinations for slot {slot_id}: {default_destinations}")
            
        except Exception as e:
            logger.error(f"❌ Error setting default destinations for slot {slot_id}: {e}")
    
    async def run(self):
        """Main scheduler loop."""
        logger.info("🚀 Starting Ad Scheduler...")
        
        try:
            await self.initialize()
            
            while True:
                await self.post_scheduled_ads()
                
                # Wait before next cycle (adjust as needed)
                logger.info("⏳ Waiting 1 hour before next posting cycle...")
                await asyncio.sleep(3600)  # 1 hour
                
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user")
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}")
        finally:
            # Cleanup
            for client in self.worker_clients:
                await client.disconnect()

async def main():
    """Main function to run the scheduler."""
    scheduler = AdScheduler()
    await scheduler.run()

if __name__ == "__main__":
    asyncio.run(main())
