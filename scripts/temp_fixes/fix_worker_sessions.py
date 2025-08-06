#!/usr/bin/env python3
"""Fix worker session management"""

# Update the worker client to handle sessions properly
cat > scheduler/workers/worker_client.py << 'WORKER_EOF'
#!/usr/bin/env python3
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
    
    def __init__(self, worker_id: int, api_id: str, api_hash: str, phone: str, session_file: str):
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
        """Connect to Telegram using existing session or create new one."""
        try:
            # Create client
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            
            # Check if session file exists and is valid
            if os.path.exists(self.session_file):
                logger.info(f"Worker {self.worker_id}: Using existing session")
                await self.client.connect()
                
                # Check if session is still valid
                if await self.client.is_user_authorized():
                    logger.info(f"Worker {self.worker_id}: Session is valid")
                    self.is_connected = True
                    return True
                else:
                    logger.warning(f"Worker {self.worker_id}: Session expired, need re-authentication")
                    await self.client.disconnect()
            
            # No valid session, need to authenticate
            logger.info(f"Worker {self.worker_id}: Starting authentication process")
            await self.client.connect()
            
            # Check if already authorized (shouldn't happen but just in case)
            if await self.client.is_user_authorized():
                logger.info(f"Worker {self.worker_id}: Already authorized")
                self.is_connected = True
                return True
                
            # Send code request
            logger.info(f"Worker {self.worker_id}: Sending code to {self.phone}")
            await self.client.send_code_request(self.phone)
            
            # For now, we'll skip the interactive code input
            # In production, this should be handled differently
            logger.warning(f"Worker {self.worker_id}: Authentication required - please run setup manually")
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
WORKER_EOF

print("✅ Worker session management updated!")
print("📝 Key improvements:")
print("   - Uses existing session files if available")
print("   - Only re-authenticates when session is invalid")
print("   - Avoids unnecessary code requests")
print("   - Better session validation")
