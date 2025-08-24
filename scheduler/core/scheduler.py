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
        
        # Initialize workers with timeout
        await self._initialize_workers()
        
        # Initialize posting service (even without workers for now)
        self.posting_service = PostingService(self.workers, self.database)
        if self.workers:
            logger.info(f"Scheduler initialized with {len(self.workers)} workers")
        else:
            logger.warning("No workers available - scheduler will run in monitoring mode only")
            
        return True
        
    async def _initialize_workers(self):
        """Initialize worker accounts with timeout."""
        logger.info("Initializing worker accounts...")
        
        # Load worker credentials from config
        from ..config.worker_config import WorkerConfig
        from ..workers.worker_client import WorkerClient
        
        worker_config = WorkerConfig()
        worker_creds = worker_config.load_workers_from_env()
        
        if not worker_creds:
            logger.warning("No worker credentials found - running without workers")
            return
        
        # Create worker clients with timeout
        self.workers = []
        for i, creds in enumerate(worker_creds):
            # Add delay between worker initializations to reduce database contention
            if i > 0:
                await asyncio.sleep(1)  # Reduced delay
            try:
                worker = WorkerClient(
                    api_id=creds.api_id,
                    api_hash=creds.api_hash,
                    phone=creds.phone,
                    session_file=creds.session_file,
                    worker_id=creds.worker_id
                )
                
                # Add timeout to worker connection
                try:
                    success = await asyncio.wait_for(worker.connect(), timeout=10.0)
                    if success:
                        self.workers.append(worker)
                        # Initialize worker limits in database
                        try:
                            await self.database.initialize_worker_limits(creds.worker_id)
                        except Exception as e:
                            logger.warning(f"Failed to initialize limits for worker {creds.worker_id}: {e}")
                        logger.info(f"Worker {creds.worker_id} initialized successfully")
                    else:
                        logger.warning(f"Worker {creds.worker_id} failed to connect")
                except asyncio.TimeoutError:
                    logger.warning(f"Worker {creds.worker_id} connection timed out after 10 seconds")
                except Exception as e:
                    logger.error(f"Worker {creds.worker_id} connection error: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize worker {creds.worker_id}: {e}")
        
        logger.info(f"Initialized {len(self.workers)} workers out of {len(worker_creds)} attempted")
        
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
                
            # Post ads (only if we have workers)
            if self.workers:
                results = await self.posting_service.post_ads(ad_slots)
                logger.info(f"Posting cycle completed: {results}")
            else:
                logger.info(f"Found {len(ad_slots)} ad slots but no workers available for posting")
                
            self.last_run = datetime.now()
            
        except Exception as e:
            logger.error(f"Posting cycle error: {e}")
            
    async def _get_active_ad_slots(self) -> List[Dict]:
        """Get active ad slots from database that are due for posting."""
        try:
            ad_slots = await self.database.get_active_ads_to_send()
            logger.info(f"Found {len(ad_slots)} active ad slots due for posting")
            return ad_slots or []
        except Exception as e:
            logger.error(f"Error getting ad slots: {e}")
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
