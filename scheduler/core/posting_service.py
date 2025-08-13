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
from ..workers.worker_assignment import WorkerAssignmentService
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
        self.assignment_service = WorkerAssignmentService(self.database)
        self.last_global_join = None
        self.global_join_count_today = 0
        
    async def post_ads(self, ad_slots: List[Dict]) -> Dict[str, Any]:
        """Post ads to their own destinations using assigned or best-available workers.

        Improvements implemented:
        - Resolve/assign workers per slot if missing/unavailable or over capacity
        - Enforce per-worker hourly/daily limits with reassignment
        - Update last_sent_at once per slot after finishing all destinations
        - Record worker usage after each attempt
        - Respect user-specific pause status for destination changes
        """
        results = {
            'total_ads': len(ad_slots),
            'successful_posts': 0,
            'failed_posts': 0,
            'errors': []
        }
        
        for ad_slot in ad_slots:
            slot_id = ad_slot.get('id')
            posted_any = False
            
            # Check if slot is paused (for destination changes)
            if ad_slot.get('is_paused', False):
                pause_reason = ad_slot.get('pause_reason', 'unknown')
                logger.info(f"Slot {slot_id} is paused: {pause_reason}, skipping")
                continue
            
            # Resolve a worker for this slot
            worker = await self._resolve_worker_for_slot(ad_slot)
            if not worker:
                msg = f"No available worker for slot {slot_id}"
                logger.warning(msg)
                results['errors'].append(msg)
                continue

            # Load destinations for this slot
            try:
                slot_type = ad_slot.get('slot_type', 'user')
                slot_dests = await self.database.get_slot_destinations(slot_id, slot_type)
            except Exception as e:
                error_msg = f"Failed to load destinations for slot {slot_id}: {e}"
                results['errors'].append(error_msg)
                self.performance_monitor.record_error(error_msg)
                continue

            if not slot_dests:
                logger.debug(f"No destinations for slot {slot_id}, skipping")
                continue

            for destination in slot_dests:
                # Check capacity before each attempt; reassign if needed
                under_limit, usage_info = await self._is_worker_under_limit(worker.worker_id)
                if not under_limit:
                    # Try to reassign to a different worker
                    reassigned = await self._reassign_worker_for_slot(ad_slot, exclude_worker_id=worker.worker_id)
                    if reassigned is None:
                        warn = f"Worker {worker.worker_id} at capacity; no reassignment available for slot {slot_id}"
                        logger.warning(warn)
                        results['errors'].append(warn)
                        break  # stop processing this slot until next cycle
                    worker = reassigned

                try:
                    success = await self._post_single_ad(ad_slot, destination, worker)
                    posted_any = True
                    if success:
                        results['successful_posts'] += 1
                    else:
                        results['failed_posts'] += 1
                    # Record usage
                    try:
                        await self.database.record_worker_post(worker.worker_id, success, None)
                    except Exception as rec_err:
                        logger.warning(f"Failed to record worker usage: {rec_err}")

                    # Delay between posts to respect anti-ban
                    await self.delay_manager.random_delay(30, 120)

                except Exception as e:
                    error_msg = f"Posting error: {str(e)}"
                    results['errors'].append(error_msg)
                    results['failed_posts'] += 1
                    self.performance_monitor.record_error(error_msg, f"Ad: {slot_id}, Dest: {destination.get('destination_id')}")

            # Update last_sent_at once per slot after finishing all destinations
            if posted_any:
                try:
                    slot_type = ad_slot.get('slot_type', 'user')
                    await self.database.update_slot_last_sent(slot_id, slot_type)
                except Exception as e:
                    logger.error(f"Failed updating last_sent_at for slot {slot_id}: {e}")
        
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
            
            # Strategy 1: Try original format
            try:
                success = await worker.send_message(destination_id, rotated_message)
                if success:
                    logger.info(f"Successfully posted to {destination_id}")
            except Exception as send_error:
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
                            success = False
                
                # Strategy 4: If it's a forum topic, try without topic ID
                elif ("cannot find any entity" in error_text or "entity not found" in error_text) and "/" in destination_id:
                    try:
                        group_only = destination_id.split('/')[0]
                        logger.info(f"Strategy 4: Retrying with group only: {group_only}")
                        success = await worker.send_message(group_only, rotated_message)
                        if success:
                            logger.info(f"Successfully posted to group (without topic): {group_only}")
                        else:
                            logger.warning(f"Strategy 4 failed: {group_only}")
                    except Exception as fallback_error:
                        logger.warning(f"Strategy 4 also failed: {fallback_error}")
                        success = False
                
                # Strategy 5: Try with t.me/ prefix for forum topics
                elif not success and "/" in destination_id and destination_id.startswith("@"):
                    try:
                        # Convert @username/topic to t.me/username/topic
                        t_me_format = destination_id.replace("@", "t.me/")
                        logger.info(f"Strategy 5: Trying t.me format: {t_me_format}")
                        success = await worker.send_message(t_me_format, rotated_message)
                        if success:
                            logger.info(f"Successfully posted using t.me format: {t_me_format}")
                        else:
                            logger.warning(f"Strategy 5 failed: {t_me_format}")
                    except Exception as t_me_error:
                        logger.warning(f"Strategy 5 also failed: {t_me_error}")
                        success = False
                
                # Strategy 6: Try with https:// prefix
                elif not success and "/" in destination_id and destination_id.startswith("@"):
                    try:
                        # Convert @username/topic to https://t.me/username/topic
                        https_format = f"https://{destination_id.replace('@', 't.me/')}"
                        logger.info(f"Strategy 6: Trying https format: {https_format}")
                        success = await worker.send_message(https_format, rotated_message)
                        if success:
                            logger.info(f"Successfully posted using https format: {https_format}")
                        else:
                            logger.warning(f"Strategy 6 failed: {https_format}")
                    except Exception as https_error:
                        logger.warning(f"Strategy 6 also failed: {https_error}")
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
                    
                    raise send_error
            
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
                group_id=destination_id,
                group_name=group_name,
                group_username=destination_id,
                fail_reason=join_result['reason'],
                worker_id=worker.worker_id,
                priority=priority
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
        if self.global_join_count_today >= 10:
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
            
            # Try to get the group entity
            try:
                group_entity = await worker.get_entity(group_name)
            except Exception as e:
                logger.warning(f"Could not get group entity for {group_name}: {e}")
                return False
            
            # Try to get forum topics
            try:
                from telethon.tl.functions.messages import GetForumTopicsRequest
                from telethon.tl.types import InputPeerChannel
                
                if hasattr(group_entity, 'id'):
                    input_peer = InputPeerChannel(group_entity.id, group_entity.access_hash)
                    topics_result = await worker(GetForumTopicsRequest(
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
                                    success = await worker.send_message(topic_destination, message)
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
                                success = await worker.send_message(topic_destination, message)
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
                    success = await worker.send_message(destination_id, message)
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
                success = await worker.send_message(destination_id, message)
                return success
                
        except Exception as e:
            logger.error(f"Error in special group posting: {e}")
            return False
