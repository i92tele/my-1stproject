#!/usr/bin/env python3
"""
Worker Client
Individual worker account management and Telegram client handling
"""

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import InviteRequestSentError, UserPrivacyRestrictedError

logger = logging.getLogger(__name__)

class WorkerClient:
    """Individual worker client for Telegram operations."""
    
    def __init__(self, api_id: str, api_hash: str, phone: str, session_file: str, worker_id: int = None):
        self.worker_id = worker_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_file = session_file
        self.client = None
        self.is_connected = False
        self.is_banned = False
        self.last_activity = None
        self.last_join_attempt = None
        self.join_attempts_today = 0
        
    async def connect(self) -> bool:
        """Connect to Telegram using existing session."""
        try:
            # Create client
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            
            # Connect to Telegram
            await self.client.connect()
            
            # Check if session is valid
            if await self.client.is_user_authorized():
                logger.info(f"Worker {self.worker_id}: Connected successfully")
                self.is_connected = True
                return True
            else:
                logger.warning(f"Worker {self.worker_id}: Session not authorized - run setup_workers.py first")
                await self.client.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            
    async def send_message(self, chat_id: str, message: str, database_manager=None) -> bool:
        """Send message to chat with ban detection."""
        if not self.is_connected:
            logger.error(f"Worker {self.worker_id}: Not connected")
            return False
        
        # Check if worker is banned from this destination
        if database_manager:
            try:
                is_banned = await database_manager.is_worker_banned(self.worker_id, chat_id)
                if is_banned:
                    logger.warning(f"Worker {self.worker_id}: Banned from {chat_id}, skipping")
                    return False
            except Exception as e:
                logger.error(f"Worker {self.worker_id}: Error checking ban status: {e}")
            
        try:
            # Handle forum topics (format: group/topic_id or t.me/group/topic_id)
            if "/" in chat_id and (chat_id.startswith("@") or chat_id.startswith("t.me/")):
                # Parse forum topic destination
                if chat_id.startswith("t.me/"):
                    # Convert t.me/social/68316 to @social and topic_id = 68316
                    parts = chat_id.replace("t.me/", "@").split("/")
                elif chat_id.startswith("@"):
                    # Handle @social/68316
                    parts = chat_id.split("/")
                else:
                    parts = chat_id.split("/")
                
                if len(parts) >= 2:
                    group_username = parts[0]
                    topic_id = int(parts[1])
                    
                    logger.info(f"Worker {self.worker_id}: Sending to forum topic {group_username}, topic {topic_id}")
                    
                    try:
                        # First, ensure we're a member of the main group
                        group_entity = await self.client.get_entity(group_username)
                        
                        # Try to join the group if not already a member
                        try:
                            await self.client(JoinChannelRequest(group_entity))
                            logger.info(f"Worker {self.worker_id}: Successfully joined {group_username}")
                        except Exception as join_error:
                            if "already a participant" not in str(join_error).lower():
                                logger.warning(f"Worker {self.worker_id}: Failed to join {group_username}: {join_error}")
                        
                        # Send message to the specific topic
                        await self.client.send_message(
                            group_entity, 
                            message, 
                            reply_to=topic_id
                        )
                        self.last_activity = time.time()
                        return True
                        
                    except Exception as forum_error:
                        logger.warning(f"Worker {self.worker_id}: Forum topic posting failed: {forum_error}")
                        # Fall back to regular posting
                        pass
            
            # Regular chat/channel posting
            await self.client.send_message(chat_id, message)
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            error_text = str(e)
            logger.error(f"Worker {self.worker_id}: Failed to send message: {error_text}")
            
            # Detect and record ban if database manager is available
            if database_manager:
                await self._handle_ban_detection(database_manager, chat_id, error_text)
            
            return False

    async def _handle_ban_detection(self, database_manager, chat_id: str, error_text: str):
        """Handle ban detection and recording."""
        try:
            error_lower = error_text.lower()
            ban_type = None
            ban_reason = error_text
            
            # Detect ban type based on error message
            if any(key in error_lower for key in ["can't write in this chat", "forbidden", "writeforbidden", "banned"]):
                ban_type = "permission_denied"
            elif "topic_closed" in error_lower:
                ban_type = "topic_closed"
            elif "rate limit" in error_lower or "wait" in error_lower:
                ban_type = "rate_limit"
            elif "content" in error_lower and ("violation" in error_lower or "not allowed" in error_lower):
                ban_type = "content_violation"
            
            # Record ban if detected
            if ban_type:
                # Estimate unban time based on ban type
                estimated_unban_time = None
                if ban_type == "rate_limit":
                    from datetime import datetime, timedelta
                    estimated_unban_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
                elif ban_type == "topic_closed":
                    from datetime import datetime, timedelta
                    estimated_unban_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
                
                await database_manager.record_worker_ban(
                    worker_id=self.worker_id,
                    destination_id=chat_id,
                    ban_type=ban_type,
                    ban_reason=ban_reason,
                    estimated_unban_time=estimated_unban_time
                )
                
                logger.warning(f"Worker {self.worker_id}: Ban detected and recorded - type: {ban_type}, dest: {chat_id}")
                
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error handling ban detection: {e}")

    async def check_ban_status(self, database_manager, destination_id: str) -> bool:
        """Check if worker is banned from a specific destination."""
        try:
            return await database_manager.is_worker_banned(self.worker_id, destination_id)
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error checking ban status: {e}")
            return False

    async def get_ban_summary(self, database_manager) -> Dict[str, Any]:
        """Get ban summary for this worker."""
        try:
            bans = await database_manager.get_worker_bans(worker_id=self.worker_id, active_only=True)
            return {
                'total_bans': len(bans),
                'bans': bans,
                'worker_id': self.worker_id
            }
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error getting ban summary: {e}")
            return {'total_bans': 0, 'bans': [], 'worker_id': self.worker_id}

    async def clear_ban(self, database_manager, destination_id: str) -> bool:
        """Clear a ban for this worker from a specific destination."""
        try:
            success = await database_manager.clear_worker_ban(self.worker_id, destination_id)
            if success:
                logger.info(f"Worker {self.worker_id}: Ban cleared for {destination_id}")
            return success
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error clearing ban: {e}")
            return False
            
    async def join_channel(self, channel_username: str) -> bool:
        """Join a channel."""
        if not self.is_connected:
            return False
            
        try:
            await self.client(JoinChannelRequest(channel_username))
            return True
        except InviteRequestSentError:
            logger.info(f"Worker {self.worker_id}: Join request sent for {channel_username}")
            return True
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Failed to join {channel_username}: {e}")
            return False



    async def is_member_of_channel(self, channel_username: str) -> bool:
        """Check if worker is already a member of a channel."""
        if not self.is_connected:
            return False
            
        try:
            from telethon.tl.functions.channels import GetParticipantRequest
            
            # Get the channel entity
            entity = await self.client.get_entity(channel_username)
            
            # Get worker's own user info
            me = await self.client.get_me()
            
            # Check if worker is participant
            participant = await self.client(GetParticipantRequest(
                channel=entity,
                participant=me
            ))
            
            return True
            
        except Exception as e:
            # If we can't get participant info, assume not a member
            return False

    async def join_channel_with_fallback(self, channel_username: str) -> Dict[str, Any]:
        """Join a channel with multiple fallback strategies."""
        if not self.is_connected:
            return {'success': False, 'reason': 'not_connected', 'method': None}
        
        # Check join rate limits
        if not self._can_attempt_join():
            return {'success': False, 'reason': 'join_limit_exceeded', 'method': None}
        
        # Check if already a member
        if await self.is_member_of_channel(channel_username):
            return {'success': True, 'reason': 'already_member', 'method': 'check'}
        
        # Try different join formats
        join_formats = self._get_join_formats(channel_username)
        
        for format_variant in join_formats:
            try:
                await self.client(JoinChannelRequest(channel=format_variant))
                self._record_join_attempt()
                logger.info(f"Worker {self.worker_id}: Successfully joined {channel_username} using {format_variant}")
                return {'success': True, 'reason': 'joined', 'method': format_variant}
                
            except InviteRequestSentError:
                self._record_join_attempt()
                logger.info(f"Worker {self.worker_id}: Join request sent for {channel_username} using {format_variant}")
                return {'success': True, 'reason': 'join_request_sent', 'method': format_variant}
                
            except UserPrivacyRestrictedError:
                logger.warning(f"Worker {self.worker_id}: Cannot join {channel_username} due to privacy settings")
                return {'success': False, 'reason': 'privacy_restricted', 'method': format_variant}
                
            except Exception as e:
                error_text = str(e).lower()
                logger.debug(f"Worker {self.worker_id}: Failed to join {channel_username} with {format_variant}: {e}")
                # Add delay between format attempts
                await asyncio.sleep(2)
                continue
        
        # If all formats failed
        return {'success': False, 'reason': 'all_formats_failed', 'method': None}

    def _can_attempt_join(self) -> bool:
        """Check if worker can attempt to join a group (rate limiting)."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if self.last_join_attempt:
            if now.date() > self.last_join_attempt.date():
                self.join_attempts_today = 0
        
        # Check daily limit (3 joins per day per worker)
        if self.join_attempts_today >= 3:
            return False
        
        # Check hourly limit (1 join per hour per worker)
        if self.last_join_attempt:
            if now - self.last_join_attempt < timedelta(hours=1):
                return False
        
        return True

    def _record_join_attempt(self):
        """Record a join attempt for rate limiting."""
        from datetime import datetime
        self.last_join_attempt = datetime.now()
        self.join_attempts_today += 1

    def _get_join_formats(self, channel_username: str) -> List[str]:
        """Get different formats to try for joining."""
        formats = []
        
        # Handle different input formats
        if channel_username.startswith('@'):
            username = channel_username[1:]
            formats = [
                channel_username,  # @username
                f"t.me/{username}",  # t.me/username
                f"https://t.me/{username}"  # https://t.me/username
            ]
        elif channel_username.startswith('https://t.me/'):
            username = channel_username.split('/')[-1]
            formats = [
                f"@{username}",  # @username
                channel_username,  # https://t.me/username
                f"t.me/{username}"  # t.me/username
            ]
        elif channel_username.startswith('t.me/'):
            username = channel_username.split('/')[-1]
            formats = [
                f"@{username}",  # @username
                f"https://{channel_username}",  # https://t.me/username
                channel_username  # t.me/username
            ]
        else:
            # Try as-is and with common prefixes
            formats = [
                channel_username,  # Try as-is
                f"@{channel_username}",  # Add @ prefix
                f"t.me/{channel_username}",  # Add t.me prefix
                f"https://t.me/{channel_username}"  # Add https prefix
            ]
        
        return formats

    async def get_channel_info(self, channel_username: str) -> Dict[str, Any]:
        """Get basic information about a channel."""
        if not self.is_connected:
            return {'error': 'not_connected'}
        
        try:
            entity = await self.client.get_entity(channel_username)
            
            return {
                'id': entity.id,
                'title': getattr(entity, 'title', 'Unknown'),
                'username': getattr(entity, 'username', None),
                'participants_count': getattr(entity, 'participants_count', 0),
                'is_channel': hasattr(entity, 'broadcast'),
                'is_group': hasattr(entity, 'megagroup'),
                'is_forum': getattr(entity, 'forum', False)
            }
            
        except Exception as e:
            return {'error': str(e)}
            
    def get_status(self) -> Dict[str, Any]:
        """Get worker status."""
        return {
            'worker_id': self.worker_id,
            'is_connected': self.is_connected,
            'is_banned': self.is_banned,
            'last_activity': self.last_activity,
            'session_file': self.session_file
        }
