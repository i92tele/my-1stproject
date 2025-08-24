from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserBannedInChannelError
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import sqlite3

class WorkerManager:
    """Manages Telegram worker accounts with rotation and cooldown tracking."""
    
    def __init__(self, db_manager, logger: logging.Logger):
        self.db = db_manager
        self.logger = logger
        self.workers: Dict[int, TelegramClient] = {}
        self.worker_configs: Dict[int, Dict[str, Any]] = {}
        self.current_worker_index = 0
        self.cooldown_minutes = 30
        
        # Worker configurations (workers 1, 2, and 4)
        self.worker_ids = [1, 2, 4]
        
    async def initialize_workers(self):
        """Initialize all worker accounts."""
        self.logger.info("🚀 Initializing worker accounts...")
        
        for worker_id in self.worker_ids:
            try:
                # Get worker credentials from environment
                api_id = os.getenv(f"WORKER_{worker_id}_API_ID")
                api_hash = os.getenv(f"WORKER_{worker_id}_API_HASH")
                phone = os.getenv(f"WORKER_{worker_id}_PHONE")
                
                if not all([api_id, api_hash, phone]):
                    self.logger.warning(f"Missing credentials for worker {worker_id}")
                    continue
                
                # Create session name
                session_name = f"sessions/worker_{worker_id}"
                os.makedirs('sessions', exist_ok=True)
                
                # Create Telethon client
                client = TelegramClient(session_name, int(api_id), api_hash)
                
                # Start client
                await client.start(phone=phone)
                
                # Test connection
                me = await client.get_me()
                if me:
                    self.workers[worker_id] = client
                    self.worker_configs[worker_id] = {
                        'api_id': api_id,
                        'api_hash': api_hash,
                        'phone': phone,
                        'username': me.username or f"worker_{worker_id}",
                        'is_active': True,
                        'last_used': None
                    }
                    
                    # Initialize worker in database
                    await self._init_worker_in_db(worker_id)
                    
                    self.logger.info(f"✅ Worker {worker_id} initialized: @{me.username}")
                else:
                    self.logger.error(f"❌ Worker {worker_id} failed to get user info")
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize worker {worker_id}: {e}")
                continue
        
        if not self.workers:
            raise Exception("No workers could be initialized")
        
        self.logger.info(f"✅ {len(self.workers)} workers initialized successfully")
    
    async def _init_worker_in_db(self, worker_id: int):
        """Initialize worker in database."""
        try:
            # Check if worker exists in cooldown table
            existing = await self._get_worker_cooldown(worker_id)
            if not existing:
                # Create new worker record
                await self._create_worker_cooldown(worker_id)
                self.logger.info(f"Created worker {worker_id} record in database")
        except Exception as e:
            self.logger.error(f"Error initializing worker {worker_id} in database: {e}")
    
    async def get_available_worker(self) -> Optional[int]:
        """Get next available worker based on round-robin and cooldowns."""
        if not self.workers:
            self.logger.error("No workers available")
            return None
        
        # Try round-robin first
        for _ in range(len(self.workers)):
            self.current_worker_index = (self.current_worker_index + 1) % len(self.worker_ids)
            worker_id = self.worker_ids[self.current_worker_index]
            
            if worker_id not in self.workers:
                continue
            
            # Check if worker is active and not in cooldown
            if await self._is_worker_available(worker_id):
                return worker_id
        
        # If no worker available in round-robin, find any available worker
        for worker_id in self.workers.keys():
            if await self._is_worker_available(worker_id):
                return worker_id
        
        self.logger.warning("No workers available (all in cooldown)")
        return None
    
    async def _is_worker_available(self, worker_id: int) -> bool:
        """Check if worker is available (not in cooldown)."""
        try:
            # Check database cooldown
            cooldown = await self._get_worker_cooldown(worker_id)
            if not cooldown or not cooldown['is_active']:
                return False
            
            # Check if worker is in cooldown period
            if cooldown['last_used_at']:
                last_used = datetime.fromisoformat(cooldown['last_used_at'])
                time_since_last_use = datetime.now() - last_used
                
                if time_since_last_use.total_seconds() < (self.cooldown_minutes * 60):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking worker {worker_id} availability: {e}")
            return False
    
    async def mark_worker_used(self, worker_id: int):
        """Mark worker as used and update cooldown."""
        try:
            # Update database cooldown
            await self._update_worker_cooldown(worker_id)
            
            # Update in-memory config
            if worker_id in self.worker_configs:
                self.worker_configs[worker_id]['last_used'] = datetime.now()
            
            self.logger.info(f"Worker {worker_id} marked as used")
            
        except Exception as e:
            self.logger.error(f"Error marking worker {worker_id} as used: {e}")
    
    async def check_worker_health(self) -> Dict[str, Any]:
        """Check health of all workers."""
        health_report = {
            'total_workers': len(self.workers),
            'active_workers': 0,
            'workers_in_cooldown': 0,
            'failed_workers': 0,
            'worker_details': {}
        }
        
        for worker_id in self.worker_ids:
            try:
                if worker_id not in self.workers:
                    health_report['failed_workers'] += 1
                    health_report['worker_details'][worker_id] = {
                        'status': 'failed',
                        'error': 'Not initialized'
                    }
                    continue
                
                # Test worker connection
                client = self.workers[worker_id]
                me = await client.get_me()
                
                if me:
                    # Check availability
                    is_available = await self._is_worker_available(worker_id)
                    
                    if is_available:
                        health_report['active_workers'] += 1
                        status = 'active'
                    else:
                        health_report['workers_in_cooldown'] += 1
                        status = 'cooldown'
                    
                    health_report['worker_details'][worker_id] = {
                        'status': status,
                        'username': me.username,
                        'is_available': is_available
                    }
                else:
                    health_report['failed_workers'] += 1
                    health_report['worker_details'][worker_id] = {
                        'status': 'failed',
                        'error': 'Cannot get user info'
                    }
                    
            except Exception as e:
                health_report['failed_workers'] += 1
                health_report['worker_details'][worker_id] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return health_report
    
    async def post_message(self, chat_id: int, message_text: str, file_id: str = None) -> bool:
        """Post message using available worker."""
        worker_id = await self.get_available_worker()
        if not worker_id:
            self.logger.error("No available workers for posting")
            return False
        
        try:
            client = self.workers[worker_id]
            
            # Post message
            if file_id:
                # Handle media message
                await client.send_file(chat_id, file_id, caption=message_text)
            else:
                # Handle text message
                await client.send_message(chat_id, message_text)
            
            # Mark worker as used
            await self.mark_worker_used(worker_id)
            
            # Log successful post
            await self._log_worker_activity(worker_id, chat_id, True)
            
            self.logger.info(f"✅ Posted to {chat_id} using worker {worker_id}")
            return True
            
        except FloodWaitError as e:
            self.logger.warning(f"Worker {worker_id} hit flood wait: {e.seconds} seconds")
            await self._handle_worker_flood_wait(worker_id, e.seconds)
            return False
            
        except UserBannedInChannelError:
            self.logger.warning(f"Worker {worker_id} banned in channel {chat_id}")
            await self._handle_worker_banned(worker_id, chat_id)
            return False
            
        except Exception as e:
            self.logger.error(f"Error posting with worker {worker_id}: {e}")
            await self._log_worker_activity(worker_id, chat_id, False, str(e))
            return False
    
    async def _handle_worker_flood_wait(self, worker_id: int, wait_seconds: int):
        """Handle flood wait for worker."""
        try:
            # Mark worker as used with extended cooldown
            await self._update_worker_cooldown(worker_id, wait_seconds)
            self.logger.info(f"Worker {worker_id} in flood wait for {wait_seconds} seconds")
        except Exception as e:
            self.logger.error(f"Error handling flood wait for worker {worker_id}: {e}")
    
    async def _handle_worker_banned(self, worker_id: int, chat_id: int):
        """Handle worker banned in channel."""
        try:
            # Log the ban
            await self._log_worker_ban(worker_id, chat_id)
            self.logger.warning(f"Worker {worker_id} banned in {chat_id}")
        except Exception as e:
            self.logger.error(f"Error handling worker ban: {e}")
    
    # Database methods for worker cooldowns
    async def _create_worker_cooldown(self, worker_id: int):
        """Create worker cooldown record in database."""
        async with self.db._lock:
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO worker_cooldowns (worker_id, last_used_at, is_active)
                    VALUES (?, ?, ?)
                ''', (worker_id, None, True))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error creating worker cooldown: {e}")
    
    async def _get_worker_cooldown(self, worker_id: int) -> Optional[Dict[str, Any]]:
        """Get worker cooldown from database."""
        async with self.db._lock:
            try:
                conn = sqlite3.connect(self.db.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM worker_cooldowns WHERE worker_id = ?
                ''', (worker_id,))
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception as e:
                self.logger.error(f"Error getting worker cooldown: {e}")
                return None
    
    async def _update_worker_cooldown(self, worker_id: int, cooldown_seconds: int = None):
        """Update worker cooldown in database."""
        async with self.db._lock:
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                if cooldown_seconds:
                    # Extended cooldown for flood wait
                    last_used = datetime.now() - timedelta(seconds=cooldown_seconds)
                else:
                    # Normal cooldown
                    last_used = datetime.now()
                
                cursor.execute('''
                    UPDATE worker_cooldowns 
                    SET last_used_at = ?, updated_at = ?
                    WHERE worker_id = ?
                ''', (last_used, datetime.now(), worker_id))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error updating worker cooldown: {e}")
    
    async def _log_worker_activity(self, worker_id: int, chat_id: int, success: bool, error: str = None):
        """Log worker activity to database."""
        async with self.db._lock:
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO worker_activity_log (worker_id, chat_id, success, error, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (worker_id, chat_id, success, error, datetime.now()))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error logging worker activity: {e}")
    
    async def _log_worker_ban(self, worker_id: int, chat_id: int):
        """Log worker ban to database."""
        async with self.db._lock:
            try:
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO worker_bans (worker_id, chat_id, banned_at)
                    VALUES (?, ?, ?)
                ''', (worker_id, chat_id, datetime.now()))
                conn.commit()
                conn.close()
            except Exception as e:
                self.logger.error(f"Error logging worker ban: {e}")
    
    async def close_workers(self):
        """Close all worker connections."""
        for worker_id, client in self.workers.items():
            try:
                await client.disconnect()
                self.logger.info(f"Worker {worker_id} disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting worker {worker_id}: {e}")
        
        self.workers.clear()
        self.logger.info("All workers closed")
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            'total_workers': len(self.workers),
            'worker_ids': list(self.workers.keys()),
            'current_worker_index': self.current_worker_index,
            'cooldown_minutes': self.cooldown_minutes
        } 