#!/usr/bin/env python3
"""
Posting Service
Core posting logic and coordination
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..workers.worker_client import WorkerClient
from ..workers.rotation import WorkerRotator
from ..workers.worker_assignment import WorkerAssignmentService
from ..anti_ban.delays import DelayManager
from ..anti_ban.content_rotation import ContentRotator
from ..anti_ban.ban_detection import BanDetector
from ..monitoring.performance_monitor import PerformanceMonitor
from restart_recovery import RestartRecovery
import random
import sqlite3

import time
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
        self.assignment_service = WorkerAssignmentService(self.database)
        self.restart_recovery = RestartRecovery(database_manager)
        # Track rate-limited destinations with expiry times
        self.rate_limited_destinations = {}  # {destination_id: expiry_timestamp}
        # Track invalid destinations
        self.invalid_destinations = set()  # Set of known invalid destination_ids
        # Track rate-limited destinations with expiry times
        self.rate_limited_destinations = {}  # {destination_id: expiry_timestamp}
        # Track invalid destinations
        self.invalid_destinations = set()  # Set of known invalid destination_ids
        self.last_global_join = None
        self.global_join_count_today = 0
        self.recovery_performed = False
        
        # Ensure required tables exist
        asyncio.create_task(self._ensure_tables())
        
    async def _ensure_tables(self):
        """Ensure all required database tables exist."""
        try:
            await self.database.ensure_worker_cooldowns_table()
            logger.info("✅ Database tables ensured")
        except Exception as e:
            logger.error(f"❌ Error ensuring tables: {e}")
    
    async def perform_restart_recovery(self) -> Dict[str, Any]:
        """Perform restart recovery if not already done."""
        if self.recovery_performed:
            logger.info("🔄 Restart recovery already performed, skipping")
            return {'status': 'already_performed'}
        
        logger.info("🔄 Performing restart recovery...")
        try:
            recovery_results = await self.restart_recovery.perform_full_recovery()
            self.recovery_performed = True
            
            # Log recovery summary
            summary = recovery_results.get('recovery_summary', {})
            if summary:
                logger.info(f"✅ Recovery completed with status: {summary.get('overall_status', 'unknown')}")
                logger.info(f"📊 Components recovered: {len(summary.get('components_recovered', []))}")
                
                if summary.get('warnings'):
                    for warning in summary['warnings']:
                        logger.warning(f"⚠️ Recovery warning: {warning}")
                
                if summary.get('recommendations'):
                    for rec in summary['recommendations']:
                        logger.info(f"💡 Recovery recommendation: {rec}")
            
            return recovery_results
            
        except Exception as e:
            logger.error(f"❌ Restart recovery failed: {e}")
            return {'error': str(e)}
    
    async def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery status."""
        return await self.restart_recovery.get_recovery_status()
        
    async def post_ads(self, ad_slots: List[Dict]) -> Dict[str, Any]:
        """Post ads to their destinations using ALL available workers simultaneously.

        Improvements implemented:
        - Parallel posting using all available workers
        - Each destination gets assigned to the best available worker
        - Multiple workers post simultaneously for maximum efficiency
        - Automatic restart recovery on first run
        """
        # Perform restart recovery on first run
        if not self.recovery_performed:
            logger.info("🔄 First posting run detected, performing restart recovery...")
            recovery_results = await self.perform_restart_recovery()
            if 'error' in recovery_results:
                logger.warning(f"⚠️ Restart recovery failed, continuing with posting: {recovery_results['error']}")
        
        results = {
            'total_ads': len(ad_slots),
            'successful_posts': 0,
            'failed_posts': 0,
            'errors': []
        }
        
        if not ad_slots:
            logger.info("No ad slots to post")
            return results
        
        # Get all available workers
        available_workers = await self.database.get_available_workers()
        if not available_workers:
            error_msg = "No available workers for posting"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
        
        logger.info(f"🚀 Starting parallel posting with {len(available_workers)} workers for {len(ad_slots)} ad slots")
        
        # Track which slots have been marked as posted to avoid duplicate updates
        posted_slots = set()
        
        # Create posting tasks for each ad slot
        posting_tasks = []
        worker_index = 0
        
        for ad_slot in ad_slots:
            slot_id = ad_slot.get('id')
            
            # Check if slot is paused
            if ad_slot.get('is_paused', False):
                pause_reason = ad_slot.get('pause_reason', 'unknown')
                logger.info(f"Slot {slot_id} is paused: {pause_reason}, skipping")
                continue
            
            # Load destinations for this slot
            slot_type = ad_slot.get('slot_type', 'user')
            slot_dests = await self.database.get_slot_destinations(slot_id, slot_type)
            
            if not slot_dests:
                logger.debug(f"No destinations for slot {slot_id}, skipping")
                continue
            
            logger.info(f"📤 Processing slot {slot_id} with {len(slot_dests)} destinations using all available workers")
            
            # Distribute destinations across multiple workers for maximum efficiency
            for i, destination in enumerate(slot_dests):
                
                # Find next available worker with proper distribution
                worker_assigned = False
                attempts = 0
                max_attempts = len(available_workers) * 2  # Try twice through all workers
                
                while not worker_assigned and attempts < max_attempts:
                    # Get next worker in round-robin fashion
                    worker_data = available_workers[worker_index % len(available_workers)]
                    worker_id = int(worker_data['worker_id'])
                    worker = self._get_worker_by_id(worker_id)
                    worker_index += 1
                    attempts += 1
                    
                    if worker:
                        # Check if this worker is under limit AND not in cooldown
                        under_limit, usage_info = await self._is_worker_under_limit(worker_id)
                        cooldown_remaining = await self._check_worker_cooldown(worker_id)
                        
                        if under_limit and cooldown_remaining == 0:
                            # Create posting task for this destination with this worker
                            task = self._post_single_destination_parallel(ad_slot, destination, worker, results, posted_slots)
                            posting_tasks.append(task)
                            logger.info(f"📝 Created task: Worker {worker_id} -> Slot {slot_id} -> {destination.get('destination_name', 'Unknown')}")
                            worker_assigned = True
                        else:
                            if not under_limit:
                                logger.debug(f"Worker {worker_id} at limit, trying next worker")
                            if cooldown_remaining > 0:
                                logger.debug(f"Worker {worker_id} in cooldown for {cooldown_remaining}s, trying next worker")
                    else:
                        logger.warning(f"Worker {worker_id} not found, trying next worker")
                
                if not worker_assigned:
                    error_msg = f"No available workers for slot {slot_id} destination {destination.get('destination_id')}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
        
        # Execute all posting tasks simultaneously
        if posting_tasks:
            logger.info(f"🔄 Executing {len(posting_tasks)} posting tasks in parallel using all {len(available_workers)} workers...")
            try:
                results_list = await asyncio.gather(*posting_tasks, return_exceptions=True)
                
                # Check for exceptions in results
                for i, result in enumerate(results_list):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Task {i} failed with exception: {result}")
                        results['failed_posts'] += 1
                        results['errors'].append(f"Task {i} failed: {result}")
                    elif result is not None:
                        logger.debug(f"Task {i} completed with result: {result}")
                
                logger.info(f"✅ Parallel posting completed: {results['successful_posts']} successful, {results['failed_posts']} failed")
                
            except Exception as e:
                logger.error(f"❌ Error during parallel execution: {e}")
                results['errors'].append(f"Parallel execution error: {e}")
        else:
            logger.warning("⚠️ No posting tasks created")
        
        return results
    
    async def _post_single_destination_parallel(self, ad_slot: Dict, destination: Dict, worker, results: Dict[str, Any], posted_slots: set = None):
        """Post a single ad slot to a single destination using the assigned worker."""
        slot_id = ad_slot.get('id')
        slot_type = ad_slot.get('slot_type', 'user')
        
        logger.info(f"🚀 Starting task: Worker {worker.worker_id} -> Slot {slot_id} -> {destination.get('destination_name', 'Unknown')}")
        # Add anti-ban delay
        await self._add_anti_ban_delay()
        # Skip rate-limited destinations
        destination_id = destination.get("destination_id", "")
        if destination_id in self.rate_limited_destinations:
            if time.time() < self.rate_limited_destinations[destination_id]:
                remaining = int(self.rate_limited_destinations[destination_id] - time.time())
                logger.info(f"⏭️ Skipping rate-limited destination {destination_id} for {remaining}s")
                results[destination_id] = {"success": False, "error": f"Rate limited for {remaining}s"}
                return False
            else:
                # Expired, remove from tracking
                del self.rate_limited_destinations[destination_id]
        # Validate destination first
        if not await self.validate_destination(destination):
            destination_id = destination.get("destination_id", "")
            results[destination_id] = {"success": False, "error": "Invalid destination"}
            return False
        # Skip rate-limited destinations
        destination_id = destination.get("destination_id", "")
        if destination_id in self.rate_limited_destinations:
            if time.time() < self.rate_limited_destinations[destination_id]:
                remaining = int(self.rate_limited_destinations[destination_id] - time.time())
                logger.info(f"⏭️ Skipping rate-limited destination {destination_id} for {remaining}s")
                results[destination_id] = {"success": False, "error": f"Rate limited for {remaining}s"}
                return False
            else:
                # Expired, remove from tracking
                del self.rate_limited_destinations[destination_id]
        # Validate destination first
        if not await self.validate_destination(destination):
            destination_id = destination.get("destination_id", "")
            results[destination_id] = {"success": False, "error": "Invalid destination"}
            return False
        
        try:
            # Check worker cooldown before posting
            cooldown_remaining = await self._check_worker_cooldown(worker.worker_id)
            if cooldown_remaining > 0:
                logger.warning(f"⏳ Worker {worker.worker_id} in cooldown for {cooldown_remaining}s, skipping")
                results['failed_posts'] += 1
                return
            
            # Random delay before posting (2-8 seconds)
            delay = random.uniform(2, 8)
            logger.info(f"⏱️ Worker {worker.worker_id} waiting {delay:.1f}s before posting...")
            await asyncio.sleep(delay)
            
            # Post the ad
            logger.debug(f"📤 Attempting to post: Worker {worker.worker_id} -> Slot {slot_id}")
            success = await self._post_single_ad(ad_slot, destination, worker)
            
            if success:
                results['successful_posts'] += 1
                logger.info(f"✅ Worker {worker.worker_id} successfully posted slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                
                # Record usage and set cooldown
                try:
                    await self.database.record_worker_post(worker.worker_id, destination.get('destination_id'))
                    # Set worker cooldown (30-60 seconds after successful post)
                    cooldown_duration = random.randint(30, 60)
                    await self._set_worker_cooldown(worker.worker_id, cooldown_duration)
                    logger.info(f"⏳ Worker {worker.worker_id} cooldown set for {cooldown_duration}s")
                except Exception as rec_err:
                    logger.warning(f"Failed to record worker usage: {rec_err}")
                
                # Update last_sent_at for the slot (only once per slot, not per destination)
                if posted_slots is not None and slot_id not in posted_slots:
                    posted_slots.add(slot_id)
                    await self._mark_slot_as_posted(slot_id, slot_type)
                
            else:
                results['failed_posts'] += 1
                logger.warning(f"❌ Worker {worker.worker_id} failed to post slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                # Set shorter cooldown for failed posts (10-20 seconds)
                cooldown_duration = random.randint(10, 20)
                await self._set_worker_cooldown(worker.worker_id, cooldown_duration)
                logger.info(f"⏳ Worker {worker.worker_id} cooldown set for {cooldown_duration}s after failure")
            
        except Exception as e:
            error_msg = f"Error posting slot {slot_id} to destination {destination.get('destination_id')}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['failed_posts'] += 1
            # Set cooldown for exceptions (15-30 seconds)
            cooldown_duration = random.randint(15, 30)
            await self._set_worker_cooldown(worker.worker_id, cooldown_duration)
            logger.info(f"⏳ Worker {worker.worker_id} cooldown set for {cooldown_duration}s after exception")
        
        logger.info(f"🏁 Completed task: Worker {worker.worker_id} -> Slot {slot_id} -> {destination.get('destination_name', 'Unknown')}")

    async def _mark_slot_as_posted(self, slot_id: int, slot_type: str):
        """Mark a slot as posted (update last_sent_at) - thread-safe version."""
        try:
            success = await self.database.update_slot_last_sent(slot_id, slot_type)
            if success:
                logger.info(f"✅ Updated last_sent_at for slot {slot_id}")
            else:
                logger.error(f"❌ Failed to update last_sent_at for slot {slot_id}")
        except Exception as e:
            logger.error(f"Failed updating last_sent_at for slot {slot_id}: {e}")

    async def _post_slot_parallel(self, ad_slot: Dict, worker, results: Dict[str, Any]):
        """Post a single ad slot to all its destinations using the assigned worker.
        This method is kept for backward compatibility but the new _post_single_destination_parallel
        method is preferred for better worker distribution."""
        slot_id = ad_slot.get('id')
        posted_any = False
        
        try:
            # Load destinations for this slot
            slot_type = ad_slot.get('slot_type', 'user')
            slot_dests = await self.database.get_slot_destinations(slot_id, slot_type)
            
            if not slot_dests:
                logger.debug(f"No destinations for slot {slot_id}, skipping")
                return
            
            logger.info(f"📤 Worker {worker.worker_id} posting slot {slot_id} to {len(slot_dests)} destinations")
            
            for destination in slot_dests:
                try:
                    # Check if worker is still under limit
                    under_limit, usage_info = await self._is_worker_under_limit(worker.worker_id)
                    if not under_limit:
                        logger.warning(f"Worker {worker.worker_id} at limit, skipping remaining destinations for slot {slot_id}")
                        break
                    
                    # Post the ad
                    success = await self._post_single_ad(ad_slot, destination, worker)
                    
                    if success:
                        posted_any = True
                        results['successful_posts'] += 1
                        logger.info(f"✅ Worker {worker.worker_id} successfully posted slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                    else:
                        results['failed_posts'] += 1
                        logger.warning(f"❌ Worker {worker.worker_id} failed to post slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                    
                    # Record usage
                    try:
                        await self.database.record_worker_post(worker.worker_id, destination.get('destination_id'))
                    except Exception as rec_err:
                        logger.warning(f"Failed to record worker usage: {rec_err}")
                    
                    # Small delay between posts to avoid spam
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    error_msg = f"Error posting slot {slot_id} to destination {destination.get('destination_id')}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_posts'] += 1
            
            # Update last_sent_at if any posts were made
            if posted_any:
                try:
                    success = await self.database.update_slot_last_sent(slot_id, slot_type)
                    if success:
                        logger.info(f"✅ Updated last_sent_at for slot {slot_id}")
                    else:
                        logger.error(f"❌ Failed to update last_sent_at for slot {slot_id}")
                except Exception as e:
                    logger.error(f"Failed updating last_sent_at for slot {slot_id}: {e}")
            else:
                logger.info(f"ℹ️ No posts made for slot {slot_id}, skipping timestamp update")
                
        except Exception as e:
            error_msg = f"Error processing slot {slot_id}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['failed_posts'] += 1
        
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
            destination_id = destination.get('destination_id')
            
            # Convert URL to username if needed
            if destination_id and destination_id.startswith('http'):
                # Extract username and topic from URL like https://t.me/CrystalMarketss/1076
                import re
                match = re.search(r't\.me/([^/]+)(?:/(\d+))?', destination_id)
                if match:
                    username = match.group(1)
                    topic_id = match.group(2)
                    if topic_id:
                        # This is a forum topic - try different formats
                        # First try with @ prefix
                        destination_id = f"@{username}/{topic_id}"
                        logger.info(f"Converted URL to forum topic: {destination_id}")
                    else:
                        # Regular group/channel
                        destination_id = f"@{username}"
                        logger.info(f"Converted URL to username: {destination_id}")
            
            # NEW: Try to join group before posting
            join_result = await self._ensure_worker_can_post(worker, destination_id)
            
            # Try to send message with multiple fallback strategies for forum topics
            success = False
            original_destination = destination_id
            last_error = None
            
            # Strategy 1: Try original format
            try:
                success = await worker.send_message(destination_id, rotated_message, self.database)
                if success:
                    logger.info(f"Successfully posted to {destination_id}")
            except Exception as send_error:
                last_error = send_error
                error_text = str(send_error).lower()
                logger.info(f"Strategy 1 failed: {error_text}")
                
                # Strategy 2: Handle TOPIC_CLOSED errors for forum topics
                if "topic_closed" in error_text and "/" in destination_id:
                    logger.info(f"Topic closed detected for {destination_id}, trying to find active topics...")
                    try:
                        # For forum topics, try to find active topics in the group
                        success = await self._handle_forum_topic_posting(worker, destination_id, rotated_message)
                        if success:
                            logger.info(f"Successfully posted to active topic in {destination_id}")
                    except Exception as topic_error:
                        logger.warning(f"Failed to find active topics: {topic_error}")
                        last_error = topic_error
                        success = False
                
                # Strategy 3: Handle special groups like Sector Market that require additional steps
                elif "cannot find any entity" in error_text or "entity not found" in error_text:
                    if "sector" in destination_id.lower() or "market" in destination_id.lower():
                        logger.info(f"Special group detected: {destination_id}, trying enhanced joining...")
                        try:
                            success = await self._handle_special_group_posting(worker, destination_id, rotated_message)
                            if success:
                                logger.info(f"Successfully posted to special group: {destination_id}")
                        except Exception as special_error:
                            logger.warning(f"Failed to post to special group: {special_error}")
                            last_error = special_error
                            success = False
                
                # Strategy 4: If it's a forum topic, try without topic ID
                elif ("cannot find any entity" in error_text or "entity not found" in error_text) and "/" in destination_id:
                    try:
                        group_only = destination_id.split('/')[0]
                        logger.info(f"Strategy 4: Retrying with group only: {group_only}")
                        success = await worker.send_message(group_only, rotated_message, self.database)
                        if success:
                            logger.info(f"Successfully posted to group (without topic): {group_only}")
                        else:
                            logger.warning(f"Strategy 4 failed: {group_only}")
                    except Exception as fallback_error:
                        logger.warning(f"Strategy 4 also failed: {fallback_error}")
                        last_error = fallback_error
                        success = False
                
                # Strategy 5: Try with t.me/ prefix for forum topics
                elif not success and "/" in destination_id and destination_id.startswith("@"):
                    try:
                        # Convert @username/topic to t.me/username/topic
                        t_me_format = destination_id.replace("@", "t.me/")
                        logger.info(f"Strategy 5: Trying t.me format: {t_me_format}")
                        success = await worker.send_message(t_me_format, rotated_message, self.database)
                        if success:
                            logger.info(f"Successfully posted using t.me format: {t_me_format}")
                        else:
                            logger.warning(f"Strategy 5 failed: {t_me_format}")
                    except Exception as t_me_error:
                        logger.warning(f"Strategy 5 also failed: {t_me_error}")
                        last_error = t_me_error
                        success = False
                
                # Strategy 6: Try with https:// prefix
                elif not success and "/" in destination_id and destination_id.startswith("@"):
                    try:
                        # Convert @username/topic to https://t.me/username/topic
                        https_format = f"https://{destination_id.replace('@', 't.me/')}"
                        logger.info(f"Strategy 6: Trying https format: {https_format}")
                        success = await worker.send_message(https_format, rotated_message, self.database)
                        if success:
                            logger.info(f"Successfully posted using https format: {https_format}")
                        else:
                            logger.warning(f"Strategy 6 failed: {https_format}")
                    except Exception as https_error:
                        logger.warning(f"Strategy 6 also failed: {https_error}")
                        last_error = https_error
                        success = False
                
                # If all strategies failed, re-raise the original error for other error handling
                if not success:
                    # Flag this destination as problematic for admin review
                    try:
                        await self.database.flag_destination_requires_manual(
                            ad_slot.get('id'), original_destination, f"All posting strategies failed: {error_text}"
                        )
                        await self.database.create_admin_warning(
                            "forum_topic_posting_failed",
                            f"Slot {ad_slot.get('id')} dest {original_destination}: All forum topic posting strategies failed",
                            severity="medium"
                        )
                        logger.warning(f"Flagged problematic forum topic: {original_destination}")
                    except Exception as flag_err:
                        logger.error(f"Failed to flag problematic destination: {flag_err}")
                    
                    raise last_error
            
            # Record posting attempt in history
            await self._record_posting_attempt(ad_slot, destination, worker, success, str(last_error) if not success and last_error else None)
            
            # Update destination health
            await self._update_destination_health(destination_id, destination.get('destination_name', destination_id), success, str(last_error) if not success and last_error else None)
            
            if success:
                # Record successful post metadata (optional analytics)
                await self._record_successful_post(ad_slot, destination, worker)
                self.performance_monitor.record_post_attempt(str(destination_id), True)
                logger.info(f"Successfully posted ad {ad_slot.get('id')} to {destination_id}")
                return True
            else:
                self.performance_monitor.record_post_attempt(str(destination_id), False)
                logger.warning(f"Failed to post ad {ad_slot.get('id')} to {destination_id}")
                return False
                
        except Exception as e:
            # Record failed posting attempt
            await self._record_posting_attempt(ad_slot, destination, worker, False, str(e))
            
            # Update destination health for failure
            await self._update_destination_health(
                destination.get('destination_id'), 
                destination.get('destination_name', destination.get('destination_id')), 
                False, 
                str(e)
            )
            
            # Known permission/captcha errors: flag destination and warn admin
            error_text = str(e)
            lower_err = error_text.lower()
            if any(key in lower_err for key in ["can't write in this chat", "topic_closed", "topic closed", "forbidden", "writeforbidden"]):
                try:
                    await self.database.flag_destination_requires_manual(
                        ad_slot.get('id'), destination.get('destination_id'), error_text
                    )
                    await self.database.create_admin_warning(
                        "destination_requires_manual",
                        f"Slot {ad_slot.get('id')} dest {destination.get('destination_id')}: {error_text}",
                        severity="high"
                    )
                    logger.warning(f"Flagged destination requires manual: slot={ad_slot.get('id')} dest={destination.get('destination_id')}")
                except Exception as flag_err:
                    logger.error(f"Failed to flag destination: {flag_err}")
                self.performance_monitor.record_error(error_text, f"Permission/captcha")
                return False

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
                'destination_id': destination.get('destination_id'),
                'worker_id': worker.worker_id,
                'posted_at': datetime.now(),
                'message': ad_slot.get('message', '')[:100]  # Truncate for storage
            }
            
            # This would update the database with posting statistics
            # await self.database.record_post(post_data)
            
        except Exception as e:
            logger.error(f"Failed to record post: {e}")

    async def _record_posting_attempt(self, ad_slot: Dict, destination: Dict, worker: WorkerClient, success: bool, error_message: str = None):
        """Record a posting attempt in the posting history."""
        try:
            import hashlib
            
            # Get slot type (user or admin)
            slot_type = ad_slot.get('slot_type', 'user')
            
            # Create content hash for duplicate detection
            message_content = ad_slot.get('content', '')
            content_hash = hashlib.md5(message_content.encode('utf-8')).hexdigest()
            
            # Detect ban type if failed
            ban_detected = False
            ban_type = None
            if not success and error_message:
                error_lower = error_message.lower()
                if any(key in error_lower for key in ["can't write in this chat", "forbidden", "writeforbidden", "banned"]):
                    ban_detected = True
                    ban_type = "permission_denied"
                elif "topic_closed" in error_lower:
                    ban_detected = True
                    ban_type = "topic_closed"
                elif "rate limit" in error_lower or "wait" in error_lower:
                    ban_detected = True
                    ban_type = "rate_limit"
            
            # Record in posting history
            await self.database.record_posting_attempt(
                worker_id=worker.worker_id,
                group_id=destination.get('destination_id'),
                success=success,
                error=error_message
            )
            
            # If ban detected, record worker ban
            if ban_detected and ban_type:
                await self._record_worker_ban(worker, destination.get('destination_id'), ban_type, error_message)
                
        except Exception as e:
            logger.error(f"Failed to record posting attempt: {e}")

    async def _update_destination_health(self, destination_id: str, destination_name: str, success: bool, error_message: str = None):
        """Update destination health statistics."""
        try:
            await self.database.update_destination_health(
                destination_id=destination_id,
                success=success
            )
        except Exception as e:
            logger.error(f"Failed to update destination health: {e}")

    async def _record_worker_ban(self, worker: WorkerClient, destination_id: str, ban_type: str, ban_reason: str):
        """Record a worker ban for a specific destination."""
        try:
            # Estimate unban time based on ban type
            estimated_unban_time = None
            if ban_type == "rate_limit":
                # Rate limits usually last 1-24 hours
                from datetime import datetime, timedelta
                estimated_unban_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
            elif ban_type == "topic_closed":
                # Topic closed might be temporary
                from datetime import datetime, timedelta
                estimated_unban_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            await self.database.record_worker_ban(
                worker_id=worker.worker_id,
                destination_id=destination_id,
                ban_type=ban_type,
                ban_reason=ban_reason,
                estimated_unban_time=estimated_unban_time
            )
            
            logger.warning(f"Recorded worker ban: worker={worker.worker_id}, dest={destination_id}, type={ban_type}")
            
        except Exception as e:
            logger.error(f"Failed to record worker ban: {e}")
            
    def _get_worker_by_id(self, worker_id: int) -> Optional[WorkerClient]:
        """Get worker by ID."""
        for worker in self.workers:
            if hasattr(worker, 'worker_id') and worker.worker_id == worker_id:
                return worker
        return None

    async def _resolve_worker_for_slot(self, ad_slot: Dict) -> Optional[WorkerClient]:
        """Ensure a valid worker is available for the given slot.
        If assigned worker is missing or at capacity, pick the best available and return it.
        """
        assigned_worker_id = ad_slot.get('assigned_worker_id')
        if assigned_worker_id is not None:
            worker = self._get_worker_by_id(int(assigned_worker_id))
            if worker:
                under_limit, _ = await self._is_worker_under_limit(worker.worker_id)
                if under_limit:
                    return worker
        # Fallback or reassignment
        best = await self.assignment_service.get_best_available_worker()
        if not best:
            return None
        return self._get_worker_by_id(int(best['worker_id']))

    async def _reassign_worker_for_slot(self, ad_slot: Dict, exclude_worker_id: int) -> Optional[WorkerClient]:
        """Pick a new worker different from exclude_worker_id."""
        best = await self.assignment_service.get_best_available_worker()
        if not best:
            return None
        if int(best['worker_id']) == int(exclude_worker_id):
            # Try to find another available worker from the pool
            try:
                available = await self.database.get_available_workers()
                for w in available:
                    if int(w['worker_id']) != int(exclude_worker_id):
                        candidate = self._get_worker_by_id(int(w['worker_id']))
                        if candidate:
                            return candidate
            except Exception:
                pass
            return None
        return self._get_worker_by_id(int(best['worker_id']))

    async def _is_worker_under_limit(self, worker_id: int) -> (bool, Dict[str, Any]):
        """Check if worker is under hourly/daily limits."""
        try:
            usage = await self.database.get_worker_usage(worker_id)
            if not usage:
                return True, {}
            hourly_posts = usage.get('hourly_posts', 0)
            daily_posts = usage.get('daily_posts', 0)
            hourly_limit = usage.get('hourly_limit', 15)
            daily_limit = usage.get('daily_limit', 150)
            under = (hourly_posts < hourly_limit) and (daily_posts < daily_limit)
            return under, usage
        except Exception as e:
            logger.warning(f"Capacity check failed for worker {worker_id}: {e}")
            return True, {}
            
    def get_status(self) -> Dict[str, Any]:
        """Get current posting service status."""
        worker_stats = self.rotator.get_worker_stats()
        performance_summary = self.performance_monitor.get_performance_summary()
        
        return {
            'workers': worker_stats,
            'performance': performance_summary,
            'service_status': 'running'
        }

    async def _ensure_worker_can_post(self, worker: WorkerClient, destination_id: str) -> Dict[str, Any]:
        """Ensure worker can post to destination by joining if needed."""
        try:
            # Check global join rate limits
            if not self._can_attempt_global_join():
                logger.warning(f"Global join limit exceeded, skipping join for {destination_id}")
                return {'success': False, 'reason': 'global_join_limit_exceeded', 'method': None}
            
            # Check if worker is already a member
            if await worker.is_member_of_channel(destination_id):
                logger.info(f"Worker {worker.worker_id} already member of {destination_id}")
                return {'success': True, 'reason': 'already_member', 'method': 'check'}
            
            # Add delay before join attempt
            await asyncio.sleep(3)
            
            # Try to join with fallback strategies
            join_result = await worker.join_channel_with_fallback(destination_id)
            
            if join_result['success']:
                # Enhanced delays after joining (anti-ban)
                if join_result['reason'] != 'already_member':
                    # Longer delay for successful joins
                    await asyncio.sleep(5)
                    self._record_global_join()
                    logger.info(f"Worker {worker.worker_id} joined {destination_id} using {join_result['method']}")
                else:
                    # Short delay for already member
                    await asyncio.sleep(1)
                
                # Log successful join
                await self._log_join_success(worker, destination_id, join_result)
                return join_result
            else:
                # Log failed join attempt
                await self._log_failed_join(worker, destination_id, join_result)
                return join_result
                
        except Exception as e:
            logger.error(f"Error ensuring worker can post to {destination_id}: {e}")
            return {'success': False, 'reason': 'error', 'method': None, 'error': str(e)}

    async def _log_join_success(self, worker: WorkerClient, destination_id: str, join_result: Dict[str, Any]):
        """Log successful join attempt."""
        try:
            # This could be expanded to log to database for analytics
            logger.info(f"Join success: Worker {worker.worker_id} -> {destination_id} ({join_result['method']})")
        except Exception as e:
            logger.error(f"Error logging join success: {e}")

    async def _log_failed_join(self, worker: WorkerClient, destination_id: str, join_result: Dict[str, Any]):
        """Log failed join attempt to database."""
        try:
            # Extract group name from destination_id
            group_name = destination_id.replace('@', '').replace('https://t.me/', '').replace('t.me/', '')
            
            # Determine priority based on destination type
            priority = 'medium'  # Default priority
            if destination_id in ['@crypto_trading', '@bitcoin_news']:  # Example high-priority groups
                priority = 'high'
            
            # Record failed join in database
            await self.database.record_failed_group_join(
                worker_id=worker.worker_id,
                group_id=destination_id,
                error=join_result['reason']
            )
            
            logger.warning(f"Failed join logged: Worker {worker.worker_id} -> {destination_id} ({join_result['reason']})")
            
        except Exception as e:
            logger.error(f"Error logging failed join: {e}")

    def _can_attempt_global_join(self) -> bool:
        """Check if global join rate limits allow another join attempt."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if self.last_global_join:
            if now.date() > self.last_global_join.date():
                self.global_join_count_today = 0
        
        # Check daily limit (10 joins per day across all workers)
        if self.global_join_count_today >= 50:  # Increased from 10 to 50 (5 per worker)
            return False
        
        # Check hourly limit (2 joins per hour across all workers)
        if self.last_global_join:
            if now - self.last_global_join < timedelta(hours=1):
                # Check if we've exceeded hourly limit
                if self.global_join_count_today >= 2:
                    return False
        
        return True

    def _record_global_join(self):
        """Record a global join attempt for rate limiting."""
        from datetime import datetime
        self.last_global_join = datetime.now()
        self.global_join_count_today += 1

    async def _handle_forum_topic_posting(self, worker: WorkerClient, destination_id: str, message: str) -> bool:
        """Handle posting to forum topics when main topic is closed."""
        try:
            # Extract group name and topic ID from forum topic
            if "/" in destination_id:
                group_name = destination_id.split('/')[0]
                original_topic_id = destination_id.split('/')[1]
            else:
                group_name = destination_id
                original_topic_id = None
            
            logger.info(f"Attempting to find active topics in {group_name}")
            
            # First, ensure worker is a member of the main group
            try:
                group_entity = await worker.get_entity(group_name)
                
                # Try to join the group if not already a member
                try:
                    from telethon.tl.functions.channels import JoinChannelRequest
                    await worker.client(JoinChannelRequest(group_entity))
                    logger.info(f"Worker {worker.worker_id}: Successfully joined {group_name}")
                except Exception as join_error:
                    if "already a participant" not in str(join_error).lower():
                        logger.warning(f"Worker {worker.worker_id}: Failed to join {group_name}: {join_error}")
                
            except Exception as e:
                logger.warning(f"Could not get group entity for {group_name}: {e}")
                return False
            
            # Try to get forum topics
            try:
                from telethon.tl.functions.messages import GetForumTopicsRequest
                from telethon.tl.types import InputPeerChannel
                
                if hasattr(group_entity, 'id'):
                    input_peer = InputPeerChannel(group_entity.id, group_entity.access_hash)
                    topics_result = await worker.client(GetForumTopicsRequest(
                        channel=input_peer,
                        offset_date=None,
                        offset_id=0,
                        offset_topic=0,
                        limit=20  # Get more topics to find the specific one
                    ))
                    
                    # First, try to find the specific topic mentioned in the destination
                    if original_topic_id:
                        logger.info(f"Looking for specific topic ID: {original_topic_id}")
                        for topic in topics_result.topics:
                            if hasattr(topic, 'id') and str(topic.id) == str(original_topic_id):
                                try:
                                    topic_destination = f"{group_name}/{topic.id}"
                                    logger.info(f"Found specific topic, trying to post: {topic_destination}")
                                    success = await worker.send_message(topic_destination, message, self.database)
                                    if success:
                                        logger.info(f"Successfully posted to specific topic: {topic_destination}")
                                        return True
                                except Exception as topic_error:
                                    logger.debug(f"Failed to post to specific topic {topic.id}: {topic_error}")
                                    break  # Don't try other topics if specific one fails
                    
                    # If specific topic not found or failed, try other active topics
                    logger.info(f"Trying alternative active topics in {group_name}")
                    for topic in topics_result.topics[:5]:  # Try first 5 topics as fallback
                        if hasattr(topic, 'id') and topic.id:
                            # Skip if this is the original topic we already tried
                            if original_topic_id and str(topic.id) == str(original_topic_id):
                                continue
                                
                            try:
                                topic_destination = f"{group_name}/{topic.id}"
                                logger.info(f"Trying to post to alternative topic: {topic_destination}")
                                success = await worker.send_message(topic_destination, message, self.database)
                                if success:
                                    logger.info(f"Successfully posted to alternative topic: {topic_destination}")
                                    return True
                            except Exception as topic_error:
                                logger.debug(f"Failed to post to alternative topic {topic.id}: {topic_error}")
                                continue
                    
                    logger.warning(f"No active topics found in {group_name}")
                    return False
                    
            except Exception as forum_error:
                logger.warning(f"Could not get forum topics for {group_name}: {forum_error}")
                # Try posting to main group as fallback
                try:
                    logger.info(f"Trying to post to main group as fallback: {group_name}")
                    success = await worker.send_message(group_name, message, self.database)
                    if success:
                        logger.info(f"Successfully posted to main group: {group_name}")
                        return True
                except Exception as fallback_error:
                    logger.warning(f"Fallback posting to main group also failed: {fallback_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error in forum topic posting: {e}")
            return False
    
    async def _handle_special_group_posting(self, worker: WorkerClient, destination_id: str, message: str) -> bool:
        """Handle posting to special groups that require additional steps."""
        try:
            logger.info(f"Handling special group posting for: {destination_id}")
            
            # For Sector Market type groups, try to navigate to the posting area
            if "sector" in destination_id.lower():
                logger.info("Detected Sector Market group, attempting enhanced joining...")
                
                # Try to get group info first
                try:
                    group_entity = await worker.get_entity(destination_id)
                    logger.info(f"Successfully got entity for {destination_id}")
                    
                    # Try posting with a slight delay to allow for group loading
                    await asyncio.sleep(2)
                    
                    # Try posting again
                    success = await worker.send_message(destination_id, message, self.database)
                    if success:
                        logger.info(f"Successfully posted to Sector Market: {destination_id}")
                        return True
                    else:
                        logger.warning(f"Failed to post to Sector Market: {destination_id}")
                        return False
                        
                except Exception as entity_error:
                    logger.warning(f"Could not get entity for {destination_id}: {entity_error}")
                    return False
            
            # For other special groups, try standard approach
            else:
                logger.info(f"Trying standard posting for special group: {destination_id}")
                success = await worker.send_message(destination_id, message, self.database)
                return success
                
        except Exception as e:
            logger.error(f"Error in special group posting: {e}")
            return False

    async def _check_worker_cooldown(self, worker_id: int) -> int:
        """Check if worker is in cooldown period."""
        try:
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cooldown_until FROM worker_cooldowns 
                WHERE worker_id = ? AND cooldown_until > datetime('now')
            """, (worker_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                cooldown_until = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                remaining = int((cooldown_until - datetime.now()).total_seconds())
                return max(0, remaining)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error checking worker cooldown: {e}")
            return 0

    async def _set_worker_cooldown(self, worker_id: int, duration_seconds: int):
        """Set worker cooldown period."""
        try:
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            
            cooldown_until = (datetime.now() + timedelta(seconds=duration_seconds)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                INSERT OR REPLACE INTO worker_cooldowns (worker_id, cooldown_until, created_at)
                VALUES (?, ?, datetime('now'))
            """, (worker_id, cooldown_until))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error setting worker cooldown: {e}")
            
    
    async def _add_anti_ban_delay(self):
        """Add random delay between posts for anti-ban protection."""
        import random
        delay = random.uniform(2, 8)  # 2-8 seconds
        logger.debug(f"🛡️ Anti-ban delay: {delay:.1f}s")
        await asyncio.sleep(delay)

    async def validate_destination(self, destination: Dict) -> bool:
        """Check if a destination is valid before attempting to post."""
        destination_id = destination.get("destination_id", "")
        destination_name = destination.get("name", "")
        
        # Skip known invalid destinations
        if hasattr(self, "invalid_destinations") and destination_id in self.invalid_destinations:
            logger.info(f"⏭️ Skipping known invalid destination: {destination_name} ({destination_id})")
            return False
            
        # Skip rate-limited destinations
        if hasattr(self, "rate_limited_destinations") and destination_id in self.rate_limited_destinations:
            if time.time() < self.rate_limited_destinations[destination_id]:
                remaining = int(self.rate_limited_destinations[destination_id] - time.time())
                logger.info(f"⏭️ Skipping rate-limited destination {destination_name} for {remaining}s")
                return False
        
        # Check format validity (basic checks)
        if "/" in destination_id and not destination_id.split("/")[0]:
            logger.warning(f"❌ Invalid destination format: {destination_name} ({destination_id})")
            if hasattr(self, "invalid_destinations"):
                self.invalid_destinations.add(destination_id)
            return False
        
        # Check for known invalid patterns
        invalid_patterns = ["@c/", "@social/", "@mafiamarketss/"]
        for pattern in invalid_patterns:
            if pattern.lower() in destination_id.lower() or pattern.lower() in destination_name.lower():
                logger.warning(f"❌ Invalid destination pattern {pattern}: {destination_name} ({destination_id})")
                if hasattr(self, "invalid_destinations"):
                    self.invalid_destinations.add(destination_id)
                return False
        
        return True
