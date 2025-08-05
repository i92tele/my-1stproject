#!/usr/bin/env python3
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError,
    InviteRequestSentError, UserPrivacyRestrictedError, SessionPasswordNeededError
)

class WorkerSystemFix:
    """Critical fixes for worker system issues."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        self.worker_clients = []
        self.worker_usage = {}
        self.max_uses_per_hour = 8  # Reduced from 10 to be safer
        self.rotation_interval = 300  # 5 minutes
        
    async def initialize_workers(self):
        """Initialize worker accounts with enhanced error handling."""
        try:
            # Clean up stale session files first
            await self.cleanup_stale_sessions()
            
            worker_index = 1
            while True:
                api_id = os.getenv(f"WORKER_{worker_index}_API_ID")
                api_hash = os.getenv(f"WORKER_{worker_index}_API_HASH")
                phone = os.getenv(f"WORKER_{worker_index}_PHONE")
                
                if not all([api_id, api_hash, phone]):
                    break
                    
                try:
                    session_name = f"sessions/worker_{worker_index}"
                    os.makedirs('sessions', exist_ok=True)
                    
                    # Create client with timeout
                    client = TelegramClient(session_name, int(api_id), api_hash)
                    
                    # Start client with timeout
                    await asyncio.wait_for(client.start(phone=phone), timeout=60)
                    
                    # Test if client is authorized
                    if await client.is_user_authorized():
                        self.worker_clients.append(client)
                        self.worker_usage[worker_index] = {
                            'uses': 0,
                            'last_used': datetime.now(),
                            'status': 'active'
                        }
                        self.logger.info(f"✅ Worker account {worker_index} connected successfully")
                    else:
                        self.logger.error(f"❌ Worker account {worker_index} not authorized")
                        
                except SessionPasswordNeededError:
                    self.logger.error(f"❌ Worker account {worker_index} needs 2FA password")
                except Exception as e:
                    self.logger.error(f"❌ Failed to connect worker account {worker_index}: {e}")
                
                worker_index += 1
            
            if not self.worker_clients:
                raise Exception("No worker accounts available")
                
            self.logger.info(f"✅ {len(self.worker_clients)} worker accounts loaded")
            
        except Exception as e:
            self.logger.error(f"Error initializing workers: {e}")
            raise
    
    async def cleanup_stale_sessions(self):
        """Clean up stale session files."""
        sessions_dir = 'sessions'
        if os.path.exists(sessions_dir):
            for file in os.listdir(sessions_dir):
                if file.endswith('.session'):
                    file_path = os.path.join(sessions_dir, file)
                    # Check if file is older than 2 hours
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if datetime.now() - file_mtime > timedelta(hours=2):
                        try:
                            os.remove(file_path)
                            self.logger.info(f"Removed stale session file: {file}")
                        except Exception as e:
                            self.logger.error(f"Failed to remove {file}: {e}")
    
    async def get_available_worker(self) -> Optional[TelegramClient]:
        """Get an available worker with usage tracking."""
        current_time = datetime.now()
        
        for i, client in enumerate(self.worker_clients):
            worker_id = i + 1
            usage = self.worker_usage.get(worker_id, {})
            
            # Check if worker is available
            if usage.get('status') == 'active':
                # Check usage limits
                last_used = usage.get('last_used', datetime.min)
                uses = usage.get('uses', 0)
                
                # Reset usage if more than 1 hour has passed
                if current_time - last_used > timedelta(hours=1):
                    uses = 0
                
                # Check if worker is within usage limits
                if uses < self.max_uses_per_hour:
                    # Update usage
                    self.worker_usage[worker_id] = {
                        'uses': uses + 1,
                        'last_used': current_time,
                        'status': 'active'
                    }
                    return client
        
        self.logger.warning("No available workers found")
        return None
    
    async def safe_send_message(self, worker_client: TelegramClient, chat, message: str) -> bool:
        """Send message with enhanced error handling and retry logic."""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid detection
                await asyncio.sleep(asyncio.random.uniform(3, 8))
                
                await worker_client.send_message(chat, message)
                self.logger.info(f"✅ Message sent successfully on attempt {attempt + 1}")
                return True
                
            except FloodWaitError as e:
                wait_time = e.seconds
                self.logger.warning(f"Flood wait error: waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                
            except ChatWriteForbiddenError:
                self.logger.error(f"Cannot send to chat: forbidden")
                return False
                
            except UserBannedInChannelError:
                self.logger.error(f"Worker banned in channel")
                return False
                
            except Exception as e:
                self.logger.error(f"Error sending message (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    delay = base_delay ** attempt  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    return False
        
        return False
    
    async def safe_join_group(self, worker_client: TelegramClient, group_username: str) -> bool:
        """Join group with enhanced error handling."""
        try:
            # Handle different group formats
            if group_username.startswith('@'):
                entity = group_username
            elif group_username.startswith('https://t.me/'):
                if '+' in group_username:
                    # Invite link
                    entity = group_username
                else:
                    # Public username
                    entity = '@' + group_username.split('/')[-1]
            else:
                entity = group_username
            
            # Try to join the group
            from telethon.tl.functions.channels import JoinChannelRequest
            
            await worker_client(JoinChannelRequest(channel=entity))
            self.logger.info(f"✅ Worker joined group: {group_username}")
            return True
            
        except InviteRequestSentError:
            self.logger.info(f"📝 Join request sent for: {group_username}")
            return True
            
        except UserPrivacyRestrictedError:
            self.logger.warning(f"🔒 Cannot join {group_username} due to privacy settings")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to join {group_username}: {e}")
            return False
    
    async def ensure_worker_in_group(self, worker_client: TelegramClient, group_username: str) -> bool:
        """Ensure worker is in group with enhanced checking."""
        try:
            from telethon.tl.functions.channels import GetParticipantRequest
            
            # Check if already in group
            try:
                entity = await worker_client.get_entity(group_username)
                participant = await worker_client(GetParticipantRequest(
                    channel=entity,
                    participant=await worker_client.get_me()
                ))
                self.logger.info(f"✅ Worker already in group: {group_username}")
                return True
            except:
                # Not in group, try to join
                return await self.safe_join_group(worker_client, group_username)
                
        except Exception as e:
            self.logger.error(f"❌ Error checking/joining group {group_username}: {e}")
            return False
    
    async def rotate_workers(self):
        """Implement worker rotation to avoid bans."""
        current_time = datetime.now()
        
        for worker_id, usage in self.worker_usage.items():
            # Check if worker needs rest
            last_used = usage.get('last_used', datetime.min)
            if current_time - last_used > timedelta(minutes=30):
                # Reset usage for rested workers
                self.worker_usage[worker_id]['uses'] = 0
                self.worker_usage[worker_id]['status'] = 'active'
                self.logger.info(f"Worker {worker_id} rested and reactivated")
    
    async def monitor_worker_health(self):
        """Monitor worker health and handle issues."""
        for worker_id, usage in self.worker_usage.items():
            if usage.get('status') == 'active':
                # Check for excessive errors
                error_count = usage.get('errors', 0)
                if error_count > 5:
                    self.logger.warning(f"Worker {worker_id} has too many errors, marking as inactive")
                    self.worker_usage[worker_id]['status'] = 'inactive'
                    
                    # Try to reactivate after 1 hour
                    asyncio.create_task(self.reactivate_worker_after_delay(worker_id, 3600))
    
    async def reactivate_worker_after_delay(self, worker_id: int, delay_seconds: int):
        """Reactivate worker after a delay."""
        await asyncio.sleep(delay_seconds)
        if worker_id in self.worker_usage:
            self.worker_usage[worker_id]['status'] = 'active'
            self.worker_usage[worker_id]['errors'] = 0
            self.logger.info(f"Worker {worker_id} reactivated after delay")
    
    async def send_ad_safely(self, ad_slot: Dict, destinations: List[str]) -> Dict:
        """Send ad safely with worker rotation and error handling."""
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for destination in destinations:
            # Get available worker
            worker = await self.get_available_worker()
            if not worker:
                results['errors'].append(f"No available workers for {destination}")
                results['failed'] += 1
                continue
            
            try:
                # Ensure worker is in group
                if not await self.ensure_worker_in_group(worker, destination):
                    results['errors'].append(f"Could not join {destination}")
                    results['failed'] += 1
                    continue
                
                # Send message
                message = ad_slot.get('ad_content', 'Check out this amazing opportunity!')
                if await self.safe_send_message(worker, destination, message):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Error sending to {destination}: {e}")
                results['failed'] += 1
        
        return results
    
    async def close_workers(self):
        """Close all worker connections."""
        for client in self.worker_clients:
            try:
                await client.disconnect()
            except Exception as e:
                self.logger.error(f"Error closing worker: {e}")

async def main():
    """Test the worker system fixes."""
    # This would be called from your main application
    pass

if __name__ == '__main__':
    asyncio.run(main()) 