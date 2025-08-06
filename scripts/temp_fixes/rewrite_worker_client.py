#!/usr/bin/env python3
"""Rewrite WorkerClient with correct constructor"""

worker_client_content = '''#!/usr/bin/env python3
"""
Worker Client
Individual worker account management and Telegram client handling
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
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
            
    def get_status(self) -> Dict[str, Any]:
        """Get worker status."""
        return {
            'worker_id': self.worker_id,
            'is_connected': self.is_connected,
            'is_banned': self.is_banned,
            'last_activity': self.last_activity,
            'session_file': self.session_file
        }
'''

# Write the fixed worker client
with open('scheduler/workers/worker_client.py', 'w') as f:
    f.write(worker_client_content)

print("✅ WorkerClient rewritten with correct constructor!")
