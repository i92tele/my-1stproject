#!/usr/bin/env python3
"""
Posting Service
Core posting logic and coordination
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..workers.worker_client import WorkerClient
from ..workers.rotation import WorkerRotator
from ..anti_ban.delays import DelayManager
from ..anti_ban.content_rotation import ContentRotator
from ..anti_ban.ban_detection import BanDetector
from ..monitoring.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)

class PostingService:
    """Core posting service that coordinates all posting operations."""
    
    def __init__(self, workers: List[WorkerClient], database_manager):
        self.workers = workers
        self.database = database_manager
        self.rotator = WorkerRotator(workers)
        self.delay_manager = DelayManager()
        self.content_rotator = ContentRotator()
        self.ban_detector = BanDetector()
        self.performance_monitor = PerformanceMonitor()
        
    async def post_ads(self, ad_slots: List[Dict], destinations: List[Dict]) -> Dict[str, Any]:
        """Post ads to destinations using worker rotation."""
        results = {
            'total_ads': len(ad_slots),
            'successful_posts': 0,
            'failed_posts': 0,
            'errors': []
        }
        
        for ad_slot in ad_slots:
            worker = self.rotator.get_next_worker()
            if not worker:
                error_msg = "No available workers"
                results['errors'].append(error_msg)
                self.performance_monitor.record_error(error_msg)
                continue
                
            # Post to each destination
            for destination in destinations:
                try:
                    success = await self._post_single_ad(ad_slot, destination, worker)
                    if success:
                        results['successful_posts'] += 1
                    else:
                        results['failed_posts'] += 1
                        
                    # Random delay between posts
                    await self.delay_manager.random_delay(30, 120)
                    
                except Exception as e:
                    error_msg = f"Posting error: {str(e)}"
                    results['errors'].append(error_msg)
                    results['failed_posts'] += 1
                    self.performance_monitor.record_error(error_msg, f"Ad: {ad_slot.get('id')}, Dest: {destination.get('id')}")
                    
        return results
        
    async def _post_single_ad(self, ad_slot: Dict, destination: Dict, worker: WorkerClient) -> bool:
        """Post a single ad to a single destination."""
        try:
            # Prepare message
            message = ad_slot.get('content', '')
            user_id = ad_slot.get('user_id')
            
            # Rotate content
            rotated_message = self.content_rotator.rotate_message(message, user_id)
            rotated_message = self.content_rotator.add_user_specific_content(rotated_message, user_id)
            rotated_message = self.content_rotator.sanitize_message(rotated_message)
            
            # Post message
            destination_id = destination.get('id')
            success = await worker.send_message(destination_id, rotated_message)
            
            if success:
                # Record successful post
                await self._record_successful_post(ad_slot, destination, worker)
                self.performance_monitor.record_post_attempt(str(destination_id), True)
                logger.info(f"Successfully posted ad {ad_slot.get('id')} to {destination_id}")
                return True
            else:
                self.performance_monitor.record_post_attempt(str(destination_id), False)
                logger.warning(f"Failed to post ad {ad_slot.get('id')} to {destination_id}")
                return False
                
        except Exception as e:
            # Handle ban detection
            ban_type = self.ban_detector.detect_ban_type(e)
            if ban_type:
                self.rotator.mark_worker_banned(worker, ban_type)
                ban_duration = self.ban_detector.get_ban_duration(ban_type, e)
                logger.warning(f"Worker banned: {ban_type}, duration: {ban_duration} minutes")
                
            self.performance_monitor.record_error(str(e), f"Single post error")
            return False
            
    async def _record_successful_post(self, ad_slot: Dict, destination: Dict, worker: WorkerClient):
        """Record successful post in database."""
        try:
            post_data = {
                'ad_slot_id': ad_slot.get('id'),
                'destination_id': destination.get('id'),
                'worker_id': worker.worker_id,
                'posted_at': datetime.now(),
                'message': ad_slot.get('message', '')[:100]  # Truncate for storage
            }
            
            # This would update the database with posting statistics
            # await self.database.record_post(post_data)
            
        except Exception as e:
            logger.error(f"Failed to record post: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current posting service status."""
        worker_stats = self.rotator.get_worker_stats()
        performance_summary = self.performance_monitor.get_performance_summary()
        
        return {
            'workers': worker_stats,
            'performance': performance_summary,
            'service_status': 'running'
        }
