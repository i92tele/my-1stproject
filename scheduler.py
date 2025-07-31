import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError, InviteRequestSentError, UserPrivacyRestrictedError
import logging
import random
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.channels import GetParticipantRequest
# from telethon.tl.functions import functions  # This import is not needed

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing modules
from database import DatabaseManager
from config import BotConfig

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config/.env')

class AdScheduler:
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
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
            logger.warning(f"🔒 Cannot join {group_username} due to privacy settings")
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
    
    async def send_ad(self, worker_client, ad_slot, destination):
        """Send a single ad to a destination."""
        try:
            # Handle different destination formats
            if destination.startswith('@'):
                entity = destination
            elif destination.startswith('https://t.me/'):
                # Extract username or invite link
                if '+' in destination:
                    # It's an invite link
                    entity = destination
                else:
                    # It's a public username link
                    entity = '@' + destination.split('/')[-1]
            else:
                entity = destination
            
            # Ensure worker is in the group
            if not await self.ensure_worker_in_group(worker_client, entity):
                logger.error(f"❌ Worker cannot access {entity}")
                return False
            
            # Get the actual entity
            try:
                chat = await worker_client.get_entity(entity)
            except Exception as e:
                logger.error(f"Could not find entity {entity}: {e}")
                return False
            
            # Send the message
            if ad_slot['ad_file_id']:
                # For now, we'll just send text
                # Later you can implement photo/video sending using the file_id
                message = ad_slot['ad_content'] or "Check out this amazing opportunity!"
            else:
                message = ad_slot['ad_content']
            
            await worker_client.send_message(chat, message)
            logger.info(f"✅ Sent ad {ad_slot['id']} to {destination}")
            return True
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait error: need to wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return False
        except ChatWriteForbiddenError:
            logger.error(f"Cannot send to {destination}: forbidden")
            return False
        except UserBannedInChannelError:
            logger.error(f"Worker banned in {destination}")
            return False
        except Exception as e:
            logger.error(f"Error sending to {destination}: {e}")
            return False
    
    async def process_due_ads(self):
        """Process all ads that are due to be sent."""
        try:
            # Get all active ads that need to be sent
            due_ads = await self.db.get_active_ads_to_send()
            
            if not due_ads:
                logger.info("No ads are due at this time")
                return
            
            logger.info(f"Found {len(due_ads)} ad(s) to process")
            
            for ad_slot in due_ads:
                # Get destinations for this ad slot
                destinations = await self.db.get_destinations_for_slot(ad_slot['id'])
                
                if not destinations:
                    logger.warning(f"Ad slot {ad_slot['id']} has no destinations set")
                    continue
                
                logger.info(f"Processing ad slot {ad_slot['id']} with {len(destinations)} destinations")
                
                # Get a worker for this batch
                worker = self.get_next_worker()
                if not worker:
                    logger.error("No worker accounts available")
                    break
                
                # Send to each destination
                successful_sends = 0
                for destination in destinations:
                    success = await self.send_ad(worker, ad_slot, destination)
                    if success:
                        successful_sends += 1
                        
                        # Anti-spam delay between sends (randomized)
                        delay = random.randint(30, 60)
                        logger.info(f"Waiting {delay} seconds before next send...")
                        await asyncio.sleep(delay)
                
                # Update last sent time if we sent to at least one destination
                if successful_sends > 0:
                    await self.db.update_ad_last_sent(ad_slot['id'])
                    logger.info(f"✅ Completed ad slot {ad_slot['id']}: {successful_sends}/{len(destinations)} sent")
                else:
                    logger.warning(f"⚠️ Ad slot {ad_slot['id']}: No messages sent successfully")
                
                # Delay between different ad campaigns
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Error in process_due_ads: {e}", exc_info=True)
    
    async def run(self):
        """Main scheduler loop."""
        logger.info("🚀 Ad Scheduler starting...")
        
        try:
            await self.initialize()
            logger.info("✅ Scheduler initialized successfully")
            
            while True:
                try:
                    logger.info("🔄 Checking for due ads...")
                    await self.process_due_ads()
                    
                    # Wait 60 seconds before next check
                    logger.info("💤 Sleeping for 60 seconds...")
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                    await asyncio.sleep(60)
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in scheduler: {e}", exc_info=True)
        finally:
            # Clean up
            for client in self.worker_clients:
                await client.disconnect()
            await self.db.close()
            logger.info("🛑 Scheduler shut down complete")

if __name__ == "__main__":
    scheduler = AdScheduler()
    asyncio.run(scheduler.run())