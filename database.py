import asyncpg
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

class DatabaseManager:
    """Handles all database operations for the AutoFarming Bot."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.pool = None

    async def initialize(self):
        """Initializes the database connection pool and creates tables."""
        try:
            self.pool = await asyncpg.create_pool(self.config.database_url)
            await self._create_tables()
            self.logger.info("Database initialized successfully with new schema.")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            raise

    async def _create_tables(self):
        """Creates the required database tables for the managed service model."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    subscription_tier VARCHAR(50),
                    subscription_expires TIMESTAMP,
                    referral_discount BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS managed_groups (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    group_name VARCHAR(255),
                    category VARCHAR(100),
                    is_active BOOLEAN DEFAULT true
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ad_slots (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    slot_number INTEGER NOT NULL,
                    ad_content TEXT,
                    ad_file_id VARCHAR(255),
                    destination_category VARCHAR(100),
                    interval_minutes INTEGER DEFAULT 60,
                    is_active BOOLEAN DEFAULT false,
                    last_sent_at TIMESTAMP,
                    worker_account_id INTEGER,
                    UNIQUE(user_id, slot_number)
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ad_destinations (
                    id SERIAL PRIMARY KEY,
                    ad_slot_id INTEGER REFERENCES ad_slots(id),
                    destination_chat_id VARCHAR(255),
                    UNIQUE(ad_slot_id, destination_chat_id)
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ad_posts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    slot_id INTEGER REFERENCES ad_slots(id),
                    destination VARCHAR(255),
                    success BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Gets user information from the database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Creates a new user in the database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    '''INSERT INTO users (user_id, username, first_name) 
                       VALUES ($1, $2, $3) 
                       ON CONFLICT (user_id) DO NOTHING''',
                    user_id, username, first_name
                )
                return True
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return False

    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Gets a user's subscription status."""
        user = await self.get_user(user_id)
        if not user or not user.get('subscription_expires'):
            return {'tier': None, 'expires': None, 'is_active': False}

        is_active = user['subscription_expires'] > datetime.now()
        return {
            'tier': user['subscription_tier'],
            'expires': user['subscription_expires'],
            'is_active': is_active
        }

    async def get_user_ad_slots(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all ad slots for a user."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM ad_slots WHERE user_id = $1 ORDER BY slot_number", user_id)
            return [dict(row) for row in rows]

    async def get_or_create_ad_slots(self, user_id: int, tier: str) -> List[Dict[str, Any]]:
        """Gets all ad slots for a user, creating them if they don't exist."""
        tier_info = self.config.get_tier_info(tier)
        if not tier_info:
            return []

        num_slots = tier_info.get('ad_slots', 0)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM ad_slots WHERE user_id = $1 ORDER BY slot_number", user_id)
            existing_slots = {row['slot_number']: dict(row) for row in rows}

            all_slots = []
            for i in range(1, num_slots + 1):
                if i not in existing_slots:
                    await conn.execute(
                        'INSERT INTO ad_slots (user_id, slot_number) VALUES ($1, $2)',
                        user_id, i
                    )
                    new_row = await conn.fetchrow("SELECT * FROM ad_slots WHERE user_id = $1 AND slot_number = $2", user_id, i)
                    all_slots.append(dict(new_row))
                else:
                    all_slots.append(existing_slots[i])

            return all_slots

    async def get_ad_slot_by_id(self, slot_id: int) -> Optional[Dict[str, Any]]:
        """Gets a single ad slot by its unique ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM ad_slots WHERE id = $1", slot_id)
            return dict(row) if row else None

    async def update_ad_slot_content(self, slot_id: int, ad_content: str, ad_file_id: Optional[str]) -> bool:
        """Updates the content of a specific ad slot."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE ad_slots SET ad_content = $1, ad_file_id = $2 WHERE id = $3",
                    ad_content, ad_file_id, slot_id
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating ad slot content: {e}")
            return False

    async def update_ad_slot_schedule(self, slot_id: int, interval_minutes: int) -> bool:
        """Updates the schedule interval for a specific ad slot."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE ad_slots SET interval_minutes = $1 WHERE id = $2",
                    interval_minutes, slot_id
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating ad slot schedule: {e}")
            return False
    
    async def update_ad_slot_status(self, slot_id: int, is_active: bool) -> bool:
        """Updates the active status of a specific ad slot."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE ad_slots SET is_active = $1 WHERE id = $2",
                    is_active, slot_id
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating ad slot status: {e}")
            return False
        
    async def get_destinations_for_slot(self, slot_id: int) -> List[str]:
        """Gets all destination chat IDs for a specific ad slot."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT destination_chat_id FROM ad_destinations WHERE ad_slot_id = $1", slot_id)
            return [row['destination_chat_id'] for row in rows]

    async def update_destinations_for_slot(self, slot_id: int, destinations: List[str]) -> bool:
        """Clears old destinations and adds a new list for a specific ad slot."""
        try:
            async with self.pool.acquire() as conn:
                # Use a transaction to ensure this is an all-or-nothing operation
                async with conn.transaction():
                    # First, delete all existing destinations for this slot
                    await conn.execute("DELETE FROM ad_destinations WHERE ad_slot_id = $1", slot_id)
                    # Then, insert the new ones if the list is not empty
                    if destinations:
                        # Use copy_records_to_table for efficient bulk inserting
                        await conn.copy_records_to_table(
                            'ad_destinations',
                            records=[(slot_id, dest) for dest in destinations],
                            columns=['ad_slot_id', 'destination_chat_id']
                        )
                return True
        except Exception as e:
            self.logger.error(f"Error updating destinations for slot: {e}")
            return False
    
    async def add_managed_group(self, group_username: str, category: str, group_id: int = None) -> bool:
        """Adds a new managed group to the database."""
        try:
            async with self.pool.acquire() as conn:
                # For now, we'll use a placeholder group_id if not provided
                # In production, you'd fetch the actual group_id from Telegram
                if group_id is None:
                    import random
                    group_id = random.randint(1000000000, 9999999999)
                
                await conn.execute(
                    '''INSERT INTO managed_groups (group_id, group_name, category) 
                       VALUES ($1, $2, $3) 
                       ON CONFLICT (group_id) DO NOTHING''',
                    group_id, group_username, category
                )
                return True
        except Exception as e:
            self.logger.error(f"Error adding managed group: {e}")
            return False
    
    async def get_managed_groups(self, category: str = None) -> List[Dict[str, Any]]:
        """Gets all managed groups, optionally filtered by category."""
        async with self.pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    "SELECT * FROM managed_groups WHERE category = $1 ORDER BY group_name",
                    category
                )
            else:
                rows = await conn.fetch("SELECT * FROM managed_groups ORDER BY category, group_name")
            return [dict(row) for row in rows]
    
    async def remove_managed_group(self, group_username: str) -> bool:
        """Removes a managed group from the database."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM managed_groups WHERE group_name = $1",
                    group_username
                )
                return result.split()[-1] != '0'  # Returns True if at least one row was deleted
        except Exception as e:
            self.logger.error(f"Error removing managed group: {e}")
            return False
    
    async def get_bot_statistics(self) -> Dict[str, int]:
        """Gets overall bot statistics."""
        async with self.pool.acquire() as conn:
            stats = {}
            
            # Total users
            result = await conn.fetchval("SELECT COUNT(*) FROM users")
            stats['total_users'] = result or 0
            
            # Active subscriptions
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE subscription_expires > $1",
                datetime.now()
            )
            stats['active_subscriptions'] = result or 0
            
            # Total ad slots
            result = await conn.fetchval("SELECT COUNT(*) FROM ad_slots")
            stats['total_ad_slots'] = result or 0
            
            # Active ads
            result = await conn.fetchval("SELECT COUNT(*) FROM ad_slots WHERE is_active = true")
            stats['active_ads'] = result or 0
            
            # Total managed groups
            result = await conn.fetchval("SELECT COUNT(*) FROM managed_groups")
            stats['total_groups'] = result or 0
            
            return stats

    async def get_active_ads_to_send(self) -> List[Dict[str, Any]]:
        """Gets all active ads that are due to be sent."""
        async with self.pool.acquire() as conn:
            # Get all active ads where last_sent_at is null or older than the interval
            rows = await conn.fetch('''
                SELECT * FROM ad_slots 
                WHERE is_active = true 
                AND ad_content IS NOT NULL 
                AND (last_sent_at IS NULL 
                     OR last_sent_at + (interval_minutes * INTERVAL '1 minute') <= CURRENT_TIMESTAMP)
                ORDER BY last_sent_at NULLS FIRST
            ''')
            return [dict(row) for row in rows]

    async def update_ad_last_sent(self, slot_id: int) -> bool:
        """Updates the last sent timestamp for an ad slot."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE ad_slots SET last_sent_at = CURRENT_TIMESTAMP WHERE id = $1",
                    slot_id
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating ad last sent: {e}")
            return False

    # --- Payment Methods ---
    
    async def create_payment(self, payment_data: dict) -> bool:
        """Creates a new payment record."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        payment_id VARCHAR(255) PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        tier VARCHAR(50) NOT NULL,
                        cryptocurrency VARCHAR(50) NOT NULL,
                        amount_usd DECIMAL(10,2) NOT NULL,
                        amount_crypto DECIMAL(20,8) NOT NULL,
                        wallet_address VARCHAR(255) NOT NULL,
                        payment_memo VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'pending',
                        tx_hash VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP
                    )
                ''')
                
                await conn.execute('''
                    INSERT INTO payments (
                        payment_id, user_id, tier, cryptocurrency, amount_usd, 
                        amount_crypto, wallet_address, payment_memo, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', 
                payment_data['payment_id'], payment_data['user_id'], payment_data['tier'],
                payment_data['cryptocurrency'], payment_data['amount_usd'], 
                payment_data['amount_crypto'], payment_data['wallet_address'],
                payment_data['payment_memo'], payment_data['expires_at']
                )
                return True
        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return False

    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Gets payment information by payment ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", payment_id)
            return dict(row) if row else None

    async def update_payment_status(self, payment_id: str, status: str, tx_hash: str = None) -> bool:
        """Updates payment status."""
        try:
            async with self.pool.acquire() as conn:
                if status == 'completed':
                    await conn.execute('''
                        UPDATE payments 
                        SET status = $1, tx_hash = $2, completed_at = CURRENT_TIMESTAMP 
                        WHERE payment_id = $3
                    ''', status, tx_hash, payment_id)
                else:
                    await conn.execute('''
                        UPDATE payments 
                        SET status = $1, tx_hash = $2 
                        WHERE payment_id = $3
                    ''', status, tx_hash, payment_id)
                return True
        except Exception as e:
            self.logger.error(f"Error updating payment status: {e}")
            return False

    async def activate_subscription(self, user_id: int, tier: str, duration_days: int = 30) -> bool:
        """Activates a user subscription after payment."""
        try:
            async with self.pool.acquire() as conn:
                # Update user subscription
                await conn.execute('''
                    UPDATE users 
                    SET subscription_tier = $1, subscription_expires = CURRENT_TIMESTAMP + INTERVAL '1 day' * $2
                    WHERE user_id = $3
                ''', tier, duration_days, user_id)
                
                # Create ad slots for the user
                tier_info = self.config.get_tier_info(tier)
                if tier_info:
                    num_slots = tier_info.get('ad_slots', 0)
                    for slot_num in range(1, num_slots + 1):
                        await conn.execute('''
                            INSERT INTO ad_slots (user_id, slot_number, is_active)
                            VALUES ($1, $2, true)
                            ON CONFLICT (user_id, slot_number) DO UPDATE SET is_active = true
                        ''', user_id, slot_num)
                
                return True
        except Exception as e:
            self.logger.error(f"Error activating subscription: {e}")
            return False

    async def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Gets all expired subscriptions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, subscription_tier, subscription_expires 
                FROM users 
                WHERE subscription_expires < CURRENT_TIMESTAMP AND subscription_tier IS NOT NULL
            ''')
            return [dict(row) for row in rows]

    async def deactivate_expired_subscriptions(self) -> int:
        """Deactivates expired subscriptions and returns count."""
        try:
            async with self.pool.acquire() as conn:
                # Get expired users
                expired_users = await conn.fetch('''
                    SELECT user_id FROM users 
                    WHERE subscription_expires < CURRENT_TIMESTAMP AND subscription_tier IS NOT NULL
                ''')
                
                if not expired_users:
                    return 0
                
                user_ids = [row['user_id'] for row in expired_users]
                
                # Deactivate subscriptions
                await conn.execute('''
                    UPDATE users 
                    SET subscription_tier = NULL, subscription_expires = NULL 
                    WHERE user_id = ANY($1)
                ''', user_ids)
                
                # Deactivate ad slots
                await conn.execute('''
                    UPDATE ad_slots 
                    SET is_active = false 
                    WHERE user_id = ANY($1)
                ''', user_ids)
                
                return len(user_ids)
        except Exception as e:
            self.logger.error(f"Error deactivating expired subscriptions: {e}")
            return 0
    
    async def get_active_ad_slots(self):
        """Get all active ad slots."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM ad_slots 
                WHERE is_active = true
            ''')
            return [dict(row) for row in rows]

    async def get_managed_groups(self) -> List[Dict[str, Any]]:
        """Get all managed groups."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM managed_groups 
                WHERE is_active = true
            ''')
            return [dict(row) for row in rows]

    async def get_ad_destinations(self, ad_slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific ad slot."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT ad.*, mg.group_name, mg.category
                FROM ad_destinations ad
                JOIN managed_groups mg ON ad.destination_chat_id = mg.group_id::text
                WHERE ad.ad_slot_id = $1
            ''', ad_slot_id)
            return [dict(row) for row in rows]

    async def log_ad_post(self, ad_slot_id: int, destination: str, status: str) -> bool:
        """Log an ad post attempt."""
        try:
            async with self.pool.acquire() as conn:
                # Get user_id from ad_slot
                slot_info = await conn.fetchrow('''
                    SELECT user_id FROM ad_slots WHERE id = $1
                ''', ad_slot_id)
                
                if slot_info:
                    await conn.execute('''
                        INSERT INTO ad_posts (user_id, slot_id, destination, success, created_at)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ''', slot_info['user_id'], ad_slot_id, destination, status == 'success')
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Error logging ad post: {e}")
            return False
