#!/usr/bin/env python3
"""
Enhanced Worker Client
Individual worker account management with advanced group joining capabilities
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import InviteRequestSentError, UserPrivacyRestrictedError

logger = logging.getLogger(__name__)

class EnhancedWorkerClient:
    """Enhanced worker client for Telegram operations with smart group joining."""
    
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
            
    async def send_message(self, chat_id: str, message: str) -> bool:
        """Send message to chat."""
        if not self.is_connected:
            logger.error(f"Worker {self.worker_id}: Not connected")
            return False
            
        try:
            await self.client.send_message(chat_id, message)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Failed to send message: {e}")
            return False

    async def is_member_of_channel(self, channel_username: str) -> bool:
        """Check if worker is already a member of a channel."""
        if not self.is_connected:
            return False
            
        try:
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
        
        # Check if already a member
        if await self.is_member_of_channel(channel_username):
            return {'success': True, 'reason': 'already_member', 'method': 'check'}
        
        # Check join limits
        if not self._can_attempt_join():
            return {'success': False, 'reason': 'join_limit_exceeded', 'method': None}
        
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
                continue
        
        # If all formats failed
        return {'success': False, 'reason': 'all_formats_failed', 'method': None}

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

    def _can_attempt_join(self) -> bool:
        """Check if worker can attempt to join a group (rate limiting)."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if self.last_join_attempt:
            if now.date() > self.last_join_attempt.date():
                self.join_attempts_today = 0
        
        # Check daily limit (3 joins per day)
        if self.join_attempts_today >= 3:
            return False
        
        # Check hourly limit (1 join per hour)
        if self.last_join_attempt:
            if now - self.last_join_attempt < timedelta(hours=1):
                return False
        
        return True

    def _record_join_attempt(self):
        """Record a join attempt for rate limiting."""
        from datetime import datetime
        self.last_join_attempt = datetime.now()
        self.join_attempts_today += 1

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
            'last_join_attempt': self.last_join_attempt,
            'join_attempts_today': self.join_attempts_today,
            'session_file': self.session_file
        }
