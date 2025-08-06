#!/usr/bin/env python3
"""
Main Scheduler
Orchestrates the entire automated posting system
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .posting_service import PostingService
from ..workers.worker_client import WorkerClient
from ..config.scheduler_config import SchedulerConfig

logger = logging.getLogger(__name__)

class AutomatedScheduler:
    """Main scheduler that orchestrates automated posting."""
    
    def __init__(self, database_manager, config: SchedulerConfig = None):
        self.database = database_manager
        self.config = config or SchedulerConfig()
        self.workers: List[WorkerClient] = []
        self.posting_service: PostingService = None
        self.is_running = False
        self.last_run = None
        
    async def initialize(self):
        """Initialize the scheduler."""
        logger.info("Initializing automated scheduler...")
        
        # Initialize workers
        await self._initialize_workers()
        
        # Initialize posting service
        if self.workers:
            self.posting_service = PostingService(self.workers, self.database)
            logger.info(f"Scheduler initialized with {len(self.workers)} workers")
        else:
            logger.error("No workers available - scheduler cannot start")
            return False
            
        return True
        
    async def _initialize_workers(self):
        """Initialize worker accounts."""
        logger.info("Initializing worker accounts...")
        
        # Load worker credentials from config
        from ..config.worker_config import WorkerConfig
        from ..workers.worker_client import WorkerClient
        
        worker_config = WorkerConfig()
        worker_creds = worker_config.load_workers_from_env()
        
        # Create worker clients
        self.workers = []
        for creds in worker_creds:
            try:
                worker = WorkerClient(
                    api_id=creds.api_id,
                    api_hash=creds.api_hash,
                    phone=creds.phone,
                    session_file=creds.session_file,
                    worker_id=creds.worker_id
                )
                success = await worker.connect()
                if success:
                    self.workers.append(worker)
                    logger.info(f"Worker {creds.worker_id} initialized successfully")
                else:
                    logger.warning(f"Worker {creds.worker_id} failed to connect")
            except Exception as e:
                logger.error(f"Failed to initialize worker {creds.worker_id}: {e}")
        
        logger.info(f"Initialized {len(self.workers)} workers")
        
    async def start(self):
        """Start the scheduler main loop."""
        if not self.posting_service:
            logger.error("Scheduler not initialized")
            return
            
        self.is_running = True
        logger.info("Starting automated scheduler...")
        
        while self.is_running:
            try:
                await self._run_posting_cycle()
                await asyncio.sleep(self.config.posting_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        logger.info("Stopping automated scheduler...")
        
    async def _run_posting_cycle(self):
        """Run a single posting cycle."""
        logger.info("Starting posting cycle...")
        
        try:
            # Get active ad slots
            ad_slots = await self._get_active_ad_slots()
            if not ad_slots:
                logger.info("No active ad slots found")
                return
                
            # Get destinations
            destinations = await self._get_destinations()
            if not destinations:
                logger.info("No destinations found")
                return
                
            # Post ads
            results = await self.posting_service.post_ads(ad_slots, destinations)
            
            # Log results
            logger.info(f"Posting cycle completed: {results}")
            self.last_run = datetime.now()
            
        except Exception as e:
            logger.error(f"Posting cycle error: {e}")
            
    async def _get_active_ad_slots(self) -> List[Dict]:
        """Get active ad slots from database."""
        try:
            ad_slots = await self.database.get_active_ad_slots()
            logger.info(f"Found {len(ad_slots)} active ad slots")
            return ad_slots or []
        except Exception as e:
            logger.error(f"Error getting ad slots: {e}")
            return []
            
    async def _get_destinations(self) -> List[Dict]:
        """Get destinations from ad slots (since they're linked)."""
        try:
            # Get destinations from the ad slots we already have
            destinations = []
            ad_slots = await self.database.get_active_ad_slots()
            
            for slot in ad_slots:
                if slot.get('destinations'):
                    for i, dest_id in enumerate(slot['destinations']):
                        dest_name = slot['destination_names'][i] if i < len(slot['destination_names']) else dest_id
                        destinations.append({
                            'id': dest_id,
                            'name': dest_name,
                            'type': 'channel',
                            'category': 'crypto',  # Default category
                            'slot_id': slot['id']
                        })
            
            # Remove duplicates
            unique_destinations = []
            seen = set()
            for dest in destinations:
                key = dest['id']
                if key not in seen:
                    seen.add(key)
                    unique_destinations.append(dest)
            
            logger.info(f"Found {len(unique_destinations)} unique destinations")
            return unique_destinations
            
        except Exception as e:
            logger.error(f"Error getting destinations: {e}")
            return []
            
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'is_running': self.is_running,
            'last_run': self.last_run,
            'worker_count': len(self.workers),
            'config': {
                'posting_interval_minutes': self.config.posting_interval_minutes,
                'max_posts_per_cycle': self.config.max_posts_per_cycle
            }
        }
