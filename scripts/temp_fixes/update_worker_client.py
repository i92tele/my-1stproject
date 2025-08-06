#!/usr/bin/env python3
"""Update worker client for better session management"""

import re

# Read the current worker client file
with open('scheduler/workers/worker_client.py', 'r') as f:
    content = f.read()

# Replace the connect method
old_connect = '''    async def connect(self) -> bool:
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
            return False'''

new_connect = '''    async def connect(self) -> bool:
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
            return False'''

# Replace the method
content = content.replace(old_connect, new_connect)

# Write back to file
with open('scheduler/workers/worker_client.py', 'w') as f:
    f.write(content)

print("✅ Worker client updated for better session management!")
