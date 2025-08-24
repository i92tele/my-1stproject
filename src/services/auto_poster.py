import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from telethon.errors import FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError
from src.services.worker_manager import WorkerManager
from src.database.manager import DatabaseManager

class AutoPoster:
    """Automated ad posting system with worker rotation and error handling."""
    
    def __init__(self, db_manager: DatabaseManager, worker_manager: WorkerManager, logger: logging.Logger):
        self.db = db_manager
        self.worker_manager = worker_manager
        self.logger = logger
        self.is_running = False
        self.cycle_interval = 60  # Check for ads every 60 seconds
        self.max_retries = 3
        self.retry_delay = 30  # seconds
        
    async def get_ads_to_post(self) -> List[Dict[str, Any]]:
        """Get active ad slots that are due for posting."""
        try:
            ads = await self.db.get_active_ads_to_send()
            self.logger.info(f"Found {len(ads)} ads ready to post")
            return ads
        except Exception as e:
            self.logger.error(f"Error getting ads to post: {e}")
            return []
    
    async def post_ad(self, ad_slot: Dict[str, Any], destinations: List[Dict[str, Any]], worker_id: int) -> Dict[str, Any]:
        """Post a single ad to all destinations using specified worker."""
        results = {
            'slot_id': ad_slot['id'],
            'total_destinations': len(destinations),
            'successful_posts': 0,
            'failed_posts': 0,
            'errors': []
        }
        
        content = ad_slot['content']
        file_id = ad_slot.get('file_id')
        
        for destination in destinations:
            try:
                chat_id = int(destination['destination_id'])
                destination_name = destination['destination_name']
                
                # Post using worker manager
                success = await self.worker_manager.post_message(
                    chat_id=chat_id,
                    message_text=content,
                    file_id=file_id
                )
                
                # Log the post attempt
                await self.db.log_ad_post(
                    slot_id=ad_slot['id'],
                    destination_id=destination['destination_id'],
                    destination_name=destination_name,
                    worker_id=worker_id,
                    success=success
                )
                
                if success:
                    results['successful_posts'] += 1
                    self.logger.info(f"✅ Posted ad {ad_slot['id']} to {destination_name}")
                else:
                    results['failed_posts'] += 1
                    error_msg = "Worker posting failed"
                    results['errors'].append({
                        'destination': destination_name,
                        'error': error_msg
                    })
                    self.logger.warning(f"❌ Failed to post ad {ad_slot['id']} to {destination_name}")
                    
            except Exception as e:
                results['failed_posts'] += 1
                error_msg = str(e)
                results['errors'].append({
                    'destination': destination['destination_name'],
                    'error': error_msg
                })
                
                # Log the failed post
                await self.db.log_ad_post(
                    slot_id=ad_slot['id'],
                    destination_id=destination['destination_id'],
                    destination_name=destination['destination_name'],
                    worker_id=worker_id,
                    success=False,
                    error=error_msg
                )
                
                self.logger.error(f"Error posting ad {ad_slot['id']} to {destination['destination_name']}: {e}")
        
        return results
    
    async def handle_posting_errors(self, error: Exception, ad_slot: Dict[str, Any], destination: Dict[str, Any]) -> bool:
        """Handle specific posting errors and determine retry strategy."""
        try:
            if isinstance(error, FloodWaitError):
                self.logger.warning(f"Flood wait for {error.seconds} seconds")
                await asyncio.sleep(error.seconds)
                return True  # Retry after flood wait
                
            elif isinstance(error, UserBannedInChannelError):
                self.logger.warning(f"Worker banned in channel {destination['destination_name']}")
                # Don't retry - worker is banned in this channel
                return False
                
            elif isinstance(error, ChatWriteForbiddenError):
                self.logger.warning(f"Cannot write to channel {destination['destination_name']}")
                # Don't retry - no write permission
                return False
                
            else:
                self.logger.error(f"Unknown error posting to {destination['destination_name']}: {error}")
                return True  # Retry unknown errors
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            return False
    
    async def process_ad_slot(self, ad_slot: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single ad slot with retry logic."""
        slot_id = ad_slot['id']
        user_id = ad_slot['user_id']
        
        # Get destinations for this slot
        destinations = await self.db.get_slot_destinations(slot_id)
        if not destinations:
            self.logger.warning(f"No destinations found for slot {slot_id}")
            return {
                'slot_id': slot_id,
                'status': 'no_destinations',
                'message': 'No destinations configured'
            }
        
        # Get available worker
        worker_id = await self.worker_manager.get_available_worker()
        if not worker_id:
            self.logger.warning(f"No available workers for slot {slot_id}")
            return {
                'slot_id': slot_id,
                'status': 'no_workers',
                'message': 'No workers available'
            }
        
        # Try posting with retries
        for attempt in range(self.max_retries):
            try:
                results = await self.post_ad(ad_slot, destinations, worker_id)
                
                # Update last_sent_at if any posts were successful
                if results['successful_posts'] > 0:
                    await self.db.update_slot_last_sent(slot_id)
                    self.logger.info(f"✅ Updated last_sent_at for slot {slot_id}")
                
                return {
                    'slot_id': slot_id,
                    'status': 'completed',
                    'results': results
                }
                
            except Exception as e:
                self.logger.error(f"Error processing slot {slot_id} (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {
                        'slot_id': slot_id,
                        'status': 'failed',
                        'error': str(e)
                    }
        
        return {
            'slot_id': slot_id,
            'status': 'failed',
            'error': 'Max retries exceeded'
        }
    
    async def run_posting_cycle(self):
        """Main posting loop that runs continuously."""
        self.logger.info("🚀 Starting AutoPoster posting cycle")
        self.is_running = True
        
        while self.is_running:
            try:
                # Get ads ready to post
                ads_to_post = await self.get_ads_to_post()
                
                if not ads_to_post:
                    self.logger.debug("No ads ready to post")
                    await asyncio.sleep(self.cycle_interval)
                    continue
                
                self.logger.info(f"📤 Processing {len(ads_to_post)} ads")
                
                # Process each ad slot
                for ad_slot in ads_to_post:
                    if not self.is_running:
                        break
                    
                    try:
                        result = await self.process_ad_slot(ad_slot)
                        
                        if result['status'] == 'completed':
                            results = result['results']
                            self.logger.info(
                                f"✅ Slot {ad_slot['id']}: {results['successful_posts']}/{results['total_destinations']} successful"
                            )
                        else:
                            self.logger.warning(f"❌ Slot {ad_slot['id']}: {result['status']} - {result.get('error', 'Unknown error')}")
                    
                    except Exception as e:
                        self.logger.error(f"Error processing ad slot {ad_slot['id']}: {e}")
                
                # Wait before next cycle
                await asyncio.sleep(self.cycle_interval)
                
            except Exception as e:
                self.logger.error(f"Error in posting cycle: {e}")
                await asyncio.sleep(self.cycle_interval)
        
        self.logger.info("🛑 AutoPoster posting cycle stopped")
    
    async def start(self):
        """Start the AutoPoster."""
        self.logger.info("🚀 Starting AutoPoster")
        await self.run_posting_cycle()
    
    async def stop(self):
        """Stop the AutoPoster."""
        self.logger.info("🛑 Stopping AutoPoster")
        self.is_running = False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get AutoPoster status."""
        try:
            # Get worker status
            worker_health = await self.worker_manager.check_worker_health()
            
            # Get pending ads
            pending_ads = await self.get_ads_to_post()
            
            return {
                'is_running': self.is_running,
                'cycle_interval': self.cycle_interval,
                'worker_health': worker_health,
                'pending_ads_count': len(pending_ads),
                'pending_ads': pending_ads
            }
        except Exception as e:
            self.logger.error(f"Error getting AutoPoster status: {e}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }
    
    async def process_single_ad(self, slot_id: int) -> Dict[str, Any]:
        """Process a single ad slot by ID."""
        try:
            # Get the specific ad slot
            ad_slots = await self.db.get_user_slots(slot_id)
            if not ad_slots:
                return {
                    'status': 'not_found',
                    'error': f'Ad slot {slot_id} not found'
                }
            
            ad_slot = ad_slots[0]
            if not ad_slot['is_active']:
                return {
                    'status': 'inactive',
                    'error': f'Ad slot {slot_id} is not active'
                }
            
            return await self.process_ad_slot(ad_slot)
            
        except Exception as e:
            self.logger.error(f"Error processing single ad {slot_id}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Global AutoPoster instance
auto_poster = None

def initialize_auto_poster(db_manager: DatabaseManager, worker_manager: WorkerManager, logger: logging.Logger):
    """Initialize the global AutoPoster instance."""
    global auto_poster
    auto_poster = AutoPoster(db_manager, worker_manager, logger)
    return auto_poster

def get_auto_poster():
    """Get the global AutoPoster instance."""
    return auto_poster 