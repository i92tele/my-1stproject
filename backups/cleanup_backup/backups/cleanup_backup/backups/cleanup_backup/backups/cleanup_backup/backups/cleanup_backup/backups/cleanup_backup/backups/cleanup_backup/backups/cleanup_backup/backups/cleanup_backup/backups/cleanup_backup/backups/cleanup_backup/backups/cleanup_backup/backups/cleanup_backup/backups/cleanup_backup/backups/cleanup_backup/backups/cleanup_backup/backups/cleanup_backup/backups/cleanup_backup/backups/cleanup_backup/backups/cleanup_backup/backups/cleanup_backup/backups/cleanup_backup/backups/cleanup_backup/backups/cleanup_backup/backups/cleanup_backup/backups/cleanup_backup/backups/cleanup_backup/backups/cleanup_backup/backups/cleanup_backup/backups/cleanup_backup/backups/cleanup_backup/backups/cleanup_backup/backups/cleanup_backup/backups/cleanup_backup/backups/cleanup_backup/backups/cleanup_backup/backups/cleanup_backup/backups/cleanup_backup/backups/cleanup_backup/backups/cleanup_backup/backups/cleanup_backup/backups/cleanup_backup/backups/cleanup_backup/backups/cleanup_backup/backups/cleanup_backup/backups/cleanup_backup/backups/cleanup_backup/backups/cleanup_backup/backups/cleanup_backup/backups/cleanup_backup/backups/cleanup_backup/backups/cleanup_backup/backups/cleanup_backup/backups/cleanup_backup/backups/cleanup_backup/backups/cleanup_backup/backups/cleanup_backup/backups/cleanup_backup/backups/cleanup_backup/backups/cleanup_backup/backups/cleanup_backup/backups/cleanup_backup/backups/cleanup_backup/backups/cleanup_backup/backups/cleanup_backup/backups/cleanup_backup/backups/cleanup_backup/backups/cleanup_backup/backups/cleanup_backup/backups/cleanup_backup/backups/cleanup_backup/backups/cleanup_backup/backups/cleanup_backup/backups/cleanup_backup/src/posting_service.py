import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .database import DatabaseManager
from .worker_manager import WorkerManager
from .auto_poster import AutoPoster
from .payment_processor import get_payment_processor

class PostingService:
    """Background service for automated ad posting and subscription management."""
    
    def __init__(self, db_manager: DatabaseManager, logger: logging.Logger):
        self.db = db_manager
        self.logger = logger
        self.is_running = False
        self.service_task = None
        
        # Initialize components
        self.worker_manager = None
        self.auto_poster = None
        self.payment_processor = None
        
        # Service configuration
        self.posting_cycle_interval = 60  # minutes
        self.cleanup_interval = 1440  # 24 hours in minutes
        self.anti_ban_delay_min = 30  # minimum delay between posts per worker
        self.anti_ban_delay_max = 120  # maximum delay between posts per worker
        self.max_posts_per_cycle = 50  # maximum posts per cycle to prevent spam
        
        # Service state
        self.last_posting_cycle = None
        self.last_cleanup = None
        self.total_posts_sent = 0
        self.total_posts_failed = 0
        self.service_start_time = None
        
        # Statistics
        self.cycle_stats = {
            'total_cycles': 0,
            'successful_posts': 0,
            'failed_posts': 0,
            'expired_subscriptions_cleaned': 0,
            'last_cycle_duration': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the posting service and its components."""
        try:
            self.logger.info("🚀 Initializing PostingService...")
            
            # Initialize worker manager
            self.worker_manager = WorkerManager(self.db, self.logger)
            await self.worker_manager.initialize_workers()
            
            # Initialize auto poster
            self.auto_poster = AutoPoster(self.db, self.worker_manager, self.logger)
            
            # Initialize payment processor
            self.payment_processor = get_payment_processor()
            if self.payment_processor:
                await self.payment_processor.initialize()
            
            self.logger.info("✅ PostingService initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize PostingService: {e}")
            return False
    
    async def start_service(self):
        """Start the main service loop."""
        if self.is_running:
            self.logger.warning("PostingService is already running")
            return
        
        self.is_running = True
        self.service_start_time = datetime.now()
        self.logger.info("🚀 Starting PostingService background service")
        
        try:
            # Start the main service loop
            while self.is_running:
                try:
                    # Run posting cycle
                    await self.run_posting_cycle()
                    
                    # Run cleanup if needed
                    await self.cleanup_expired_subscriptions()
                    
                    # Wait for next cycle
                    await asyncio.sleep(self.posting_cycle_interval * 60)
                    
                except asyncio.CancelledError:
                    self.logger.info("🛑 PostingService cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Error in PostingService main loop: {e}")
                    # Wait before retrying
                    await asyncio.sleep(60)
                    
        except Exception as e:
            self.logger.error(f"Critical error in PostingService: {e}")
        finally:
            self.is_running = False
            self.logger.info("🛑 PostingService stopped")
    
    async def run_posting_cycle(self):
        """Run one complete posting cycle."""
        cycle_start = datetime.now()
        self.logger.info("📤 Starting posting cycle...")
        
        try:
            # Get active ads that are due for posting
            ads_to_post = await self.db.get_active_ads_to_send()
            
            if not ads_to_post:
                self.logger.debug("No ads ready to post in this cycle")
                return
            
            self.logger.info(f"📤 Found {len(ads_to_post)} ads ready to post")
            
            # Apply anti-ban rules and rate limiting
            posts_this_cycle = 0
            successful_posts = 0
            failed_posts = 0
            
            for ad_slot in ads_to_post:
                if not self.is_running:
                    break
                
                if posts_this_cycle >= self.max_posts_per_cycle:
                    self.logger.warning(f"Reached maximum posts per cycle ({self.max_posts_per_cycle})")
                    break
                
                try:
                    # Check if user subscription is still active
                    user_id = ad_slot['user_id']
                    subscription = await self.db.get_user_subscription(user_id)
                    
                    if not subscription or not subscription['is_active']:
                        self.logger.warning(f"User {user_id} subscription expired, skipping ad slot {ad_slot['id']}")
                        continue
                    
                    # Process the ad slot
                    result = await self.auto_poster.process_ad_slot(ad_slot)
                    
                    if result['status'] == 'completed':
                        successful_posts += 1
                        self.total_posts_sent += 1
                        self.logger.info(f"✅ Posted ad slot {ad_slot['id']} successfully")
                    else:
                        failed_posts += 1
                        self.total_posts_failed += 1
                        self.logger.warning(f"❌ Failed to post ad slot {ad_slot['id']}: {result.get('error', 'Unknown error')}")
                    
                    posts_this_cycle += 1
                    
                    # Anti-ban delay between posts
                    delay = self._calculate_anti_ban_delay()
                    if delay > 0:
                        self.logger.debug(f"Anti-ban delay: {delay} seconds")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    self.logger.error(f"Error processing ad slot {ad_slot['id']}: {e}")
                    failed_posts += 1
                    self.total_posts_failed += 1
            
            # Update cycle statistics
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.cycle_stats['total_cycles'] += 1
            self.cycle_stats['successful_posts'] += successful_posts
            self.cycle_stats['failed_posts'] += failed_posts
            self.cycle_stats['last_cycle_duration'] = cycle_duration
            self.last_posting_cycle = datetime.now()
            
            self.logger.info(
                f"📊 Posting cycle completed: {successful_posts} successful, {failed_posts} failed "
                f"(Duration: {cycle_duration:.1f}s)"
            )
            
        except Exception as e:
            self.logger.error(f"Error in posting cycle: {e}")
    
    async def cleanup_expired_subscriptions(self):
        """Clean up expired subscriptions."""
        try:
            # Check if cleanup is needed (run once per day)
            if (self.last_cleanup and 
                (datetime.now() - self.last_cleanup).total_seconds() < self.cleanup_interval * 60):
                return
            
            self.logger.info("🧹 Starting subscription cleanup...")
            
            # Get expiring subscriptions (within 7 days)
            expiring_subscriptions = await self.db.get_expiring_subscriptions(7)
            
            cleaned_count = 0
            for subscription in expiring_subscriptions:
                try:
                    user_id = subscription['user_id']
                    
                    # Check if subscription has actually expired
                    subscription_info = await self.db.get_user_subscription(user_id)
                    if not subscription_info or not subscription_info['is_active']:
                        # Deactivate all user's ad slots
                        user_slots = await self.db.get_user_slots(user_id)
                        for slot in user_slots:
                            await self.db.deactivate_slot(slot['id'])
                        
                        cleaned_count += 1
                        self.logger.info(f"🧹 Deactivated slots for expired subscription: user {user_id}")
                        
                except Exception as e:
                    self.logger.error(f"Error cleaning up subscription for user {subscription['user_id']}: {e}")
            
            self.cycle_stats['expired_subscriptions_cleaned'] += cleaned_count
            self.last_cleanup = datetime.now()
            
            self.logger.info(f"🧹 Cleanup completed: {cleaned_count} expired subscriptions cleaned")
            
        except Exception as e:
            self.logger.error(f"Error in subscription cleanup: {e}")
    
    def _calculate_anti_ban_delay(self) -> float:
        """Calculate anti-ban delay between posts."""
        import random
        
        # Base delay with some randomness
        base_delay = random.uniform(self.anti_ban_delay_min, self.anti_ban_delay_max)
        
        # Add extra delay if we've been posting frequently
        if self.cycle_stats['successful_posts'] > 100:
            base_delay *= 1.5
        
        return base_delay
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive service status for admin monitoring."""
        try:
            # Get worker status
            worker_status = None
            if self.worker_manager:
                worker_status = await self.worker_manager.check_worker_health()
            
            # Get auto poster status
            auto_poster_status = None
            if self.auto_poster:
                auto_poster_status = await self.auto_poster.get_status()
            
            # Calculate uptime
            uptime = None
            if self.service_start_time:
                uptime = datetime.now() - self.service_start_time
            
            # Get pending ads count
            pending_ads = await self.db.get_active_ads_to_send()
            
            # Get system statistics
            system_stats = await self.db.get_stats()
            
            return {
                'service_status': {
                    'is_running': self.is_running,
                    'uptime': str(uptime) if uptime else None,
                    'last_posting_cycle': self.last_posting_cycle.isoformat() if self.last_posting_cycle else None,
                    'last_cleanup': self.last_cleanup.isoformat() if self.last_cleanup else None,
                    'posting_cycle_interval': self.posting_cycle_interval,
                    'cleanup_interval': self.cleanup_interval
                },
                'statistics': {
                    'total_posts_sent': self.total_posts_sent,
                    'total_posts_failed': self.total_posts_failed,
                    'cycle_stats': self.cycle_stats,
                    'pending_ads_count': len(pending_ads),
                    'system_stats': system_stats
                },
                'components': {
                    'worker_manager': worker_status,
                    'auto_poster': auto_poster_status,
                    'payment_processor': 'available' if self.payment_processor else 'not_available'
                },
                'anti_ban_config': {
                    'min_delay': self.anti_ban_delay_min,
                    'max_delay': self.anti_ban_delay_max,
                    'max_posts_per_cycle': self.max_posts_per_cycle
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            return {
                'error': str(e),
                'is_running': self.is_running
            }
    
    async def stop_service(self):
        """Stop the posting service gracefully."""
        self.logger.info("🛑 Stopping PostingService...")
        self.is_running = False
        
        # Cancel the service task if it exists
        if self.service_task and not self.service_task.done():
            self.service_task.cancel()
            try:
                await self.service_task
            except asyncio.CancelledError:
                pass
        
        # Close components
        if self.worker_manager:
            await self.worker_manager.close_workers()
        
        if self.payment_processor:
            await self.payment_processor.close()
        
        self.logger.info("✅ PostingService stopped successfully")
    
    def stop(self):
        """Stop the posting service (synchronous wrapper)."""
        self.logger.info("Stopping posting service...")
        self.is_running = False
        # The actual stopping is handled by stop_service() which is async
    
    async def restart_service(self):
        """Restart the posting service."""
        self.logger.info("🔄 Restarting PostingService...")
        await self.stop_service()
        await asyncio.sleep(5)  # Brief pause before restart
        await self.start_service()
    
    def update_config(self, **kwargs):
        """Update service configuration."""
        allowed_configs = {
            'posting_cycle_interval',
            'cleanup_interval', 
            'anti_ban_delay_min',
            'anti_ban_delay_max',
            'max_posts_per_cycle'
        }
        
        for key, value in kwargs.items():
            if key in allowed_configs:
                setattr(self, key, value)
                self.logger.info(f"Updated config: {key} = {value}")
            else:
                self.logger.warning(f"Unknown config key: {key}")

# Global PostingService instance
posting_service = None

def initialize_posting_service(db_manager: DatabaseManager, logger: logging.Logger):
    """Initialize the global PostingService instance."""
    global posting_service
    posting_service = PostingService(db_manager, logger)
    return posting_service

def get_posting_service():
    """Get the global PostingService instance."""
    return posting_service

async def start_posting_service_background():
    """Start the posting service as a background task."""
    global posting_service
    if posting_service:
        # Initialize the service
        if await posting_service.initialize():
            # Start the service in the background
            posting_service.service_task = asyncio.create_task(posting_service.start_service())
            return posting_service.service_task
        else:
            raise Exception("Failed to initialize PostingService")
    else:
        raise Exception("PostingService not initialized")

