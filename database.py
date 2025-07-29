import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

class DatabaseManager:
    """Handle all database operations using PostgreSQL."""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.pool = None
        
    async def initialize(self):
        """Initialize database connection pool and create tables."""
        try:
            self.pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=1,
                max_size=10
            )
            await self._create_tables()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
    
    async def _create_tables(self):
        """Create required database tables."""
        async with self.pool.acquire() as conn:
            # Users table - ADDED worker_session_name COLUMN
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    subscription_tier VARCHAR(50),
                    subscription_expires TIMESTAMP,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    worker_session_name VARCHAR(255)
                )
            ''')
            
            # Destinations table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS destinations (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    destination_type VARCHAR(50),
                    destination_id VARCHAR(255),
                    destination_name VARCHAR(255),
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Payments table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    payment_id VARCHAR(255) UNIQUE,
                    user_id BIGINT REFERENCES users(user_id),
                    amount_usd DECIMAL(10,2),
                    amount_crypto DECIMAL(20,10),
                    cryptocurrency VARCHAR(50),
                    wallet_address VARCHAR(255),
                    payment_memo VARCHAR(50),
                    status VARCHAR(50),
                    tier VARCHAR(50),
                    tx_hash VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')

            # NEW TABLE for scheduled ads
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_ads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE REFERENCES users(user_id),
                    message_text TEXT,
                    message_file_id VARCHAR(255),
                    interval_minutes INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    last_sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Message stats table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS message_stats (
                    user_id BIGINT,
                    date DATE,
                    message_count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    # User Management
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None
    
    async def create_or_update_user(self, user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> bool:
        """Create or update user record."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name) VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = COALESCE($2, users.username),
                        first_name = COALESCE($3, users.first_name),
                        last_name = COALESCE($4, users.last_name),
                        updated_at = CURRENT_TIMESTAMP
                ''', user_id, username, first_name, last_name)
                return True
        except Exception as e:
            self.logger.error(f"Error creating/updating user: {e}")
            return False
    
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's subscription information."""
        user = await self.get_user(user_id)
        if not user or not user.get('subscription_expires'):
            return {'tier': None, 'expires': None, 'is_active': False}
        is_active = user['subscription_expires'] > datetime.now()
        return {'tier': user['subscription_tier'], 'expires': user['subscription_expires'], 'is_active': is_active}
    
    # Destination Management
    async def add_destination(self, user_id: int, dest_type: str, dest_id: str, dest_name: str) -> bool:
        """Add a forwarding destination."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('INSERT INTO destinations (user_id, destination_type, destination_id, destination_name) VALUES ($1, $2, $3, $4)',
                                   user_id, dest_type, dest_id, dest_name)
                return True
        except Exception as e:
            self.logger.error(f"Error adding destination: {e}")
            return False

    async def get_destinations(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's forwarding destinations."""
        query = "SELECT * FROM destinations WHERE user_id = $1"
        if active_only:
            query += " AND is_active = true"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            return [dict(row) for row in rows]

    # Scheduler functions
    async def get_due_ads(self) -> List[Dict[str, Any]]:
        """Get all ads that are due to be sent."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM scheduled_ads
                WHERE is_active = true AND (
                    last_sent_at IS NULL OR 
                    last_sent_at + (interval_minutes * INTERVAL '1 minute') <= NOW()
                )
            ''')
            return [dict(row) for row in rows]

    async def update_ad_last_sent(self, ad_id: int) -> bool:
        """Update the last_sent_at timestamp for an ad."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE scheduled_ads SET last_sent_at = NOW(), updated_at = NOW() WHERE id = $1", ad_id)
                return True
        except Exception as e:
            self.logger.error(f"Error updating ad last sent time: {e}")
            return False

    async def get_ad_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a scheduled ad by user ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM scheduled_ads WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def set_ad_message(self, user_id: int, text: str = None, file_id: str = None) -> bool:
        """Set or update the ad message for a user. Creates a record if none exists."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO scheduled_ads (user_id, message_text, message_file_id, interval_minutes, last_sent_at)
                    VALUES ($1, $2, $3, 60, NULL)
                    ON CONFLICT (user_id) DO UPDATE SET
                        message_text = $2,
                        message_file_id = $3,
                        updated_at = NOW()
                ''', user_id, text, file_id)
                return True
        except Exception as e:
            self.logger.error(f"Error setting ad message: {e}")
            return False
            
    async def set_ad_schedule(self, user_id: int, interval: int) -> bool:
        """Update the interval for a user's ad."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE scheduled_ads SET interval_minutes = $1 WHERE user_id = $2", interval, user_id)
                return True
        except Exception as e:
            self.logger.error(f"Error setting ad schedule: {e}")
            return False

    async def toggle_ad_status(self, user_id: int, is_active: bool) -> bool:
        """Pause or resume a user's ad."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE scheduled_ads SET is_active = $1 WHERE user_id = $2", is_active, user_id)
                return True
        except Exception as e:
            self.logger.error(f"Error toggling ad status: {e}")
            return False
