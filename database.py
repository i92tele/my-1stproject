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
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=1,
                max_size=10
            )
            
            # Create tables
            await self._create_tables()
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
    
    async def _create_tables(self):
        """Create required database tables."""
        async with self.pool.acquire() as conn:
            # Users table
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Security logs table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS security_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    event_type VARCHAR(100),
                    description TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Admin alerts table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admin_alerts (
                    id SERIAL PRIMARY KEY,
                    message TEXT,
                    priority VARCHAR(20),
                    is_read BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            return dict(row) if row else None
    
    async def create_or_update_user(self, user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> bool:
        """Create or update user record."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
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
        if not user:
            return None
            
        if user['subscription_expires']:
            is_active = user['subscription_expires'] > datetime.now()
        else:
            is_active = False
            
        return {
            'tier': user['subscription_tier'],
            'expires': user['subscription_expires'],
            'is_active': is_active
        }
    
    async def update_subscription(self, user_id: int, tier: str, duration_days: int) -> bool:
        """Update user's subscription."""
        try:
            async with self.pool.acquire() as conn:
                expires = datetime.now() + timedelta(days=duration_days)
                await conn.execute('''
                    UPDATE users 
                    SET subscription_tier = $1, subscription_expires = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = $3
                ''', tier, expires, user_id)
                return True
        except Exception as e:
            self.logger.error(f"Error updating subscription: {e}")
            return False
    
    # Destination Management
    
    async def add_destination(self, user_id: int, dest_type: str, 
                            dest_id: str, dest_name: str) -> bool:
        """Add a forwarding destination."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO destinations (user_id, destination_type, destination_id, destination_name)
                    VALUES ($1, $2, $3, $4)
                ''', user_id, dest_type, dest_id, dest_name)
                return True
        except Exception as e:
            self.logger.error(f"Error adding destination: {e}")
            return False
    
    async def get_destinations(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's forwarding destinations."""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM destinations WHERE user_id = $1"
            params = [user_id]
            
            if active_only:
                query += " AND is_active = true"
                
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def remove_destination(self, user_id: int, dest_id: int) -> bool:
        """Remove a forwarding destination."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE destinations 
                    SET is_active = false 
                    WHERE user_id = $1 AND id = $2
                ''', user_id, dest_id)
                return result.split()[-1] != '0'
        except Exception as e:
            self.logger.error(f"Error removing destination: {e}")
            return False
    
    # Payment Management
    
    async def create_payment(self, payment_data: Dict) -> bool:
        """Create a payment record."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO payments (
                        payment_id, user_id, amount_usd, amount_crypto,
                        cryptocurrency, wallet_address, payment_memo,
                        status, tier, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''', 
                payment_data['payment_id'], payment_data['user_id'],
                payment_data['amount_usd'], payment_data['amount_crypto'],
                payment_data['cryptocurrency'], payment_data['wallet_address'],
                payment_data['payment_memo'], payment_data['status'],
                payment_data['tier'], payment_data['expires_at']
                )
                return True
        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return False
    
    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM payments WHERE payment_id = $1",
                payment_id
            )
            return dict(row) if row else None
    
    async def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status."""
        try:
            async with self.pool.acquire() as conn:
                if status == 'completed':
                    await conn.execute('''
                        UPDATE payments 
                        SET status = $1, completed_at = CURRENT_TIMESTAMP
                        WHERE payment_id = $2
                    ''', status, payment_id)
                else:
                    await conn.execute('''
                        UPDATE payments 
                        SET status = $1
                        WHERE payment_id = $2
                    ''', status, payment_id)
                return True
        except Exception as e:
            self.logger.error(f"Error updating payment status: {e}")
            return False
    
    # Statistics
    
    async def increment_message_count(self, user_id: int) -> bool:
        """Increment user's daily message count."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO message_stats (user_id, date, message_count)
                    VALUES ($1, CURRENT_DATE, 1)
                    ON CONFLICT (user_id, date) DO UPDATE SET
                        message_count = message_stats.message_count + 1
                ''', user_id)
                return True
        except Exception as e:
            self.logger.error(f"Error incrementing message count: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get overall bot statistics."""
        async with self.pool.acquire() as conn:
            # Total users
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            
            # Active subscriptions
            active_subs = await conn.fetchval('''
                SELECT COUNT(*) FROM users 
                WHERE subscription_expires > NOW()
            ''')
            
            # Messages today
            messages_today = await conn.fetchval('''
                SELECT COALESCE(SUM(message_count), 0) FROM message_stats 
                WHERE date = CURRENT_DATE
            ''')
            
            # Revenue this month
            revenue_month = await conn.fetchval('''
                SELECT COALESCE(SUM(amount_usd), 0) FROM payments 
                WHERE status = 'completed' 
                AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW())
                AND EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM NOW())
            ''')
            
            return {
                'total_users': total_users,
                'active_subscriptions': active_subs,
                'messages_today': messages_today,
                'revenue_this_month': float(revenue_month)
            }
    
    # Admin functions
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from the database."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
            return [dict(row) for row in rows]
    
    async def create_admin_alert(self, message: str, priority: str = 'normal') -> bool:
        """Create an admin alert."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO admin_alerts (message, priority)
                    VALUES ($1, $2)
                ''', message, priority)
                return True
        except Exception as e:
            self.logger.error(f"Error creating admin alert: {e}")
            return False