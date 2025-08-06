#!/usr/bin/env python3
"""
Ban Detection
Detects and handles various types of bans and restrictions
"""

import logging
from typing import Dict, Any, Optional
from telethon.errors import (
    FloodWaitError, UserPrivacyRestrictedError, ChatWriteForbiddenError,
    ChannelPrivateError, UserBannedInChannelError, UserNotParticipantError
)

logger = logging.getLogger(__name__)

class BanDetector:
    """Detects and handles various ban scenarios."""
    
    def __init__(self):
        self.ban_types = {
            'flood_wait': FloodWaitError,
            'privacy_restricted': UserPrivacyRestrictedError,
            'write_forbidden': ChatWriteForbiddenError,
            'channel_private': ChannelPrivateError,
            'user_banned': UserBannedInChannelError,
            'not_participant': UserNotParticipantError
        }
        
    def detect_ban_type(self, exception) -> Optional[str]:
        """Detect the type of ban from exception."""
        for ban_type, exception_class in self.ban_types.items():
            if isinstance(exception, exception_class):
                return ban_type
        return None
        
    def get_ban_duration(self, ban_type: str, exception) -> int:
        """Get recommended ban duration in minutes."""
        if ban_type == 'flood_wait':
            return getattr(exception, 'seconds', 60) // 60
        elif ban_type == 'privacy_restricted':
            return 120  # 2 hours
        elif ban_type == 'write_forbidden':
            return 240  # 4 hours
        elif ban_type == 'channel_private':
            return 60   # 1 hour
        elif ban_type == 'user_banned':
            return 1440 # 24 hours
        elif ban_type == 'not_participant':
            return 30   # 30 minutes
        else:
            return 60   # Default 1 hour
            
    def should_retry(self, ban_type: str, retry_count: int) -> bool:
        """Determine if we should retry after ban."""
        max_retries = {
            'flood_wait': 3,
            'privacy_restricted': 1,
            'write_forbidden': 2,
            'channel_private': 2,
            'user_banned': 0,  # Don't retry if banned
            'not_participant': 3
        }
        return retry_count < max_retries.get(ban_type, 1)
