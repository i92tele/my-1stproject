import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class DatabaseManager:
    """Database manager for AutoFarming Bot.
    
    Handles all SQLite database operations including users, subscriptions,
    ad slots, payments, and analytics with proper error handling and logging.
    """

    def __init__(self, db_path: str, logger):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            logger: Logger instance for error logging
        """
        self.db_path = db_path
        self.logger = logger
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database with required tables.
        
        Creates all necessary tables if they don't exist:
        - users: User information and subscriptions
        - ad_slots: Advertising slot management
        - slot_destinations: Destinations for each ad slot
        - payments: Payment tracking
        - message_stats: Message analytics
        - worker_cooldowns: Worker account management
        - worker_activity_log: Worker activity tracking
        
        Raises:
            Exception: If database initialization fails
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        subscription_tier TEXT,
                        subscription_expires TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create ad_slots table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ad_slots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        slot_number INTEGER,
                        content TEXT,
                        file_id TEXT,
                        is_active BOOLEAN DEFAULT 0,
                        interval_minutes INTEGER DEFAULT 60,
                        last_sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Create slot_destinations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS slot_destinations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_id INTEGER,
                        destination_type TEXT,
                        destination_id TEXT,
                        destination_name TEXT,
                        alias TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (slot_id) REFERENCES ad_slots(id)
                    )
                ''')

                # Create payments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payment_id TEXT UNIQUE,
                        user_id INTEGER,
                        amount REAL,
                        currency TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        timeout_minutes INTEGER,
                        updated_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Create message_stats table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS message_stats (
                        user_id INTEGER,
                        date DATE,
                        message_count INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, date),
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Create worker_cooldowns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_cooldowns (
                        worker_id INTEGER PRIMARY KEY,
                        last_used_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create worker_activity_log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER,
                        chat_id INTEGER,
                        success BOOLEAN,
                        error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (worker_id) REFERENCES worker_cooldowns(worker_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_bans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER,
                        chat_id INTEGER,
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (worker_id) REFERENCES worker_cooldowns(worker_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS managed_groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id TEXT UNIQUE,
                        group_name TEXT,
                        category TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ad_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_id INTEGER,
                        destination_id TEXT,
                        destination_name TEXT,
                        worker_id INTEGER,
                        success BOOLEAN,
                        error TEXT,
                        posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (slot_id) REFERENCES ad_slots(id),
                        FOREIGN KEY (worker_id) REFERENCES worker_cooldowns(worker_id)
                    )
                ''')

                conn.commit()
                conn.close()
                self.logger.info("Database initialized successfully")

            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                raise

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by user ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User information dict or None if user not found
            
        Raises:
            Exception: If database operation fails
        """
        if not user_id or user_id <= 0:
            self.logger.warning(f"Invalid user_id: {user_id}")
            return None
            
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception as e:
                self.logger.error(f"Error getting user {user_id}: {e}")
                return None

    async def create_or_update_user(self, user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> bool:
        """Create or update user record.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username (optional)
            first_name: User's first name (optional)
            last_name: User's last name (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If database operation fails
        """
        if not user_id or user_id <= 0:
            self.logger.warning(f"Invalid user_id: {user_id}")
            return False
            
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, datetime.now()))
                conn.commit()
                conn.close()
                self.logger.info(f"User {user_id} created/updated successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error creating/updating user {user_id}: {e}")
                return False

    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's subscription information."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT subscription_tier, subscription_expires 
                FROM users 
                WHERE user_id = ? AND subscription_expires > ?
            ''', (user_id, datetime.now()))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'tier': row['subscription_tier'],
                    'expires': row['subscription_expires'],
                    'is_active': True
                }
            return None

    async def update_subscription(self, user_id: int, tier: str, duration_days: int) -> bool:
        """Update user's subscription."""
        async with self._lock:
            try:
                expires = datetime.now() + timedelta(days=duration_days)
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (tier, expires, datetime.now(), user_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating subscription: {e}")
                return False

    async def get_user_slots(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all ad slots for a user."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM ad_slots WHERE user_id = ? ORDER BY slot_number
                ''', (user_id,))
                slots = [dict(row) for row in cursor.fetchall()]
                
                # Get destinations for each slot
                for slot in slots:
                    cursor.execute('''
                        SELECT * FROM slot_destinations 
                        WHERE slot_id = ? AND is_active = 1
                    ''', (slot['id'],))
                    slot['destinations'] = [dict(row) for row in cursor.fetchall()]
                
                conn.close()
                return slots
            except Exception as e:
                self.logger.error(f"Error getting user slots: {e}")
                return []

    async def create_ad_slot(self, user_id: int, slot_number: int) -> Optional[int]:
        """Create a new ad slot for a user."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ad_slots (user_id, slot_number, created_at)
                    VALUES (?, ?, ?)
                ''', (user_id, slot_number, datetime.now()))
                slot_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return slot_id
            except Exception as e:
                self.logger.error(f"Error creating ad slot: {e}")
                return None

    async def update_slot_content(self, slot_id: int, content: str, file_id: str = None) -> bool:
        """Update slot content."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET content = ?, file_id = ?, updated_at = ?
                    WHERE id = ?
                ''', (content, file_id, datetime.now(), slot_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating slot content: {e}")
                return False

    async def add_slot_destination(self, slot_id: int, dest_type: str, dest_id: str, dest_name: str) -> bool:
        """Add destination to a slot."""
        async with self._lock:
            try:
                # Check if slot already has 10 destinations
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM slot_destinations 
                    WHERE slot_id = ? AND is_active = 1
                ''', (slot_id,))
                count = cursor.fetchone()[0]
                
                if count >= 10:
                    conn.close()
                    return False
                
                cursor.execute('''
                    INSERT INTO slot_destinations (slot_id, destination_type, destination_id, destination_name, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (slot_id, dest_type, dest_id, dest_name, datetime.now()))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error adding slot destination: {e}")
                return False

    async def remove_slot_destination(self, slot_id: int, dest_id: str) -> bool:
        """Remove destination from a slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE slot_destinations 
                    SET is_active = 0, updated_at = ?
                    WHERE slot_id = ? AND destination_id = ?
                ''', (datetime.now(), slot_id, dest_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error removing slot destination: {e}")
                return False

    async def get_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get all destinations for a slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM slot_destinations 
                    WHERE slot_id = ? AND is_active = 1
                ''', (slot_id,))
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return destinations
            except Exception as e:
                self.logger.error(f"Error getting slot destinations: {e}")
                return []

    async def activate_slot(self, slot_id: int) -> bool:
        """Activate a slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET is_active = 1, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now(), slot_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error activating slot: {e}")
                return False

    async def deactivate_slot(self, slot_id: int) -> bool:
        """Deactivate a slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET is_active = 0, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now(), slot_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error deactivating slot: {e}")
                return False

    # Legacy methods for backward compatibility
    async def add_destination(self, user_id: int, dest_type: str, 
                            dest_id: str, dest_name: str) -> bool:
        """Legacy method - redirects to slot system."""
        # Get user's first slot or create one
        slots = await self.get_user_slots(user_id)
        if not slots:
            slot_id = await self.create_ad_slot(user_id, 1)
        else:
            slot_id = slots[0]['id']
        
        return await self.add_slot_destination(slot_id, dest_type, dest_id, dest_name)

    async def get_destinations(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Legacy method - get destinations from first slot."""
        slots = await self.get_user_slots(user_id)
        if not slots:
            return []
        
        return await self.get_slot_destinations(slots[0]['id'])

    async def get_destination_by_id(self, dest_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Legacy method - get destination by ID."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sd.* FROM slot_destinations sd
                    JOIN ad_slots s ON sd.slot_id = s.id
                    WHERE sd.id = ? AND s.user_id = ? AND sd.is_active = 1
                ''', (dest_id, user_id))
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception as e:
                self.logger.error(f"Error getting destination by ID: {e}")
                return None

    async def set_destination_alias(self, dest_id: int, user_id: int, alias: str) -> bool:
        """Legacy method - set destination alias."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE slot_destinations 
                    SET alias = ?, updated_at = ?
                    WHERE id = ? AND slot_id IN (
                        SELECT id FROM ad_slots WHERE user_id = ?
                    )
                ''', (alias, datetime.now(), dest_id, user_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error setting destination alias: {e}")
                return False

    async def remove_destination(self, user_id: int, dest_id: int) -> bool:
        """Legacy method - remove destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE slot_destinations 
                    SET is_active = 0, updated_at = ?
                    WHERE id = ? AND slot_id IN (
                        SELECT id FROM ad_slots WHERE user_id = ?
                    )
                ''', (datetime.now(), dest_id, user_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error removing destination: {e}")
                return False

    async def record_payment(self, user_id: int, payment_id: str, amount: float, 
                           currency: str, status: str, expires_at: datetime, 
                           timeout_minutes: int) -> bool:
        """Record a new payment."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (payment_id, user_id, amount, currency, status, created_at, expires_at, timeout_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (payment_id, user_id, amount, currency, status, datetime.now(), expires_at, timeout_minutes))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error recording payment: {e}")
                return False

    async def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET status = ?, updated_at = ?
                    WHERE payment_id = ?
                ''', (status, datetime.now(), payment_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating payment status: {e}")
                return False

    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by ID."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments WHERE payment_id = ?
                ''', (payment_id,))
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception as e:
                self.logger.error(f"Error getting payment: {e}")
                return None

    async def get_pending_payments(self, age_limit_minutes: int) -> List[Dict[str, Any]]:
        """Get pending payments older than specified minutes."""
        async with self._lock:
            try:
                cutoff_time = datetime.now() - timedelta(minutes=age_limit_minutes)
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE status = 'pending' AND created_at < ?
                ''', (cutoff_time,))
                payments = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return payments
            except Exception as e:
                self.logger.error(f"Error getting pending payments: {e}")
                return []

    async def get_expiring_subscriptions(self, days_from_now: int) -> List[Dict[str, Any]]:
        """Get subscriptions expiring within specified days."""
        async with self._lock:
            try:
                expiry_date = datetime.now() + timedelta(days=days_from_now)
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, subscription_tier, subscription_expires 
                    FROM users 
                    WHERE subscription_expires BETWEEN ? AND ?
                ''', (datetime.now(), expiry_date))
                subscriptions = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return subscriptions
            except Exception as e:
                self.logger.error(f"Error getting expiring subscriptions: {e}")
                return []

    async def increment_message_count(self, user_id: int) -> bool:
        """Increment message count for user."""
        async with self._lock:
            try:
                today = datetime.now().date()
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO message_stats (user_id, date, message_count)
                    VALUES (?, ?, COALESCE((
                        SELECT message_count + 1 FROM message_stats 
                        WHERE user_id = ? AND date = ?
                    ), 1))
                ''', (user_id, today, user_id, today))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error incrementing message count: {e}")
                return False

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users')
                users = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return users
            except Exception as e:
                self.logger.error(f"Error getting all users: {e}")
                return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Total users
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # Active subscriptions
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE subscription_expires > ?
                ''', (datetime.now(),))
                active_subscriptions = cursor.fetchone()[0]
                
                # Messages today
                today = datetime.now().date()
                cursor.execute('''
                    SELECT COALESCE(SUM(message_count), 0) FROM message_stats 
                    WHERE date = ?
                ''', (today,))
                messages_today = cursor.fetchone()[0]
                
                # Revenue this month (placeholder)
                revenue_this_month = 0.0
                
                conn.close()
                
                return {
                    'total_users': total_users,
                    'active_subscriptions': active_subscriptions,
                    'messages_today': messages_today,
                    'revenue_this_month': revenue_this_month
                }
            except Exception as e:
                self.logger.error(f"Error getting stats: {e}")
                return {
                    'total_users': 0,
                    'active_subscriptions': 0,
                    'messages_today': 0,
                    'revenue_this_month': 0.0
                }

    async def get_active_ads_to_send(self) -> List[Dict[str, Any]]:
        """Get active ad slots that are due for posting."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get active slots that are due for posting
                cursor.execute('''
                    SELECT s.*, u.username 
                    FROM ad_slots s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
                    )
                    ORDER BY s.last_sent_at ASC NULLS FIRST
                ''')
                
                slots = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return slots
                
            except Exception as e:
                self.logger.error(f"Error getting active ads to send: {e}")
                return []

    async def update_slot_last_sent(self, slot_id: int) -> bool:
        """Update the last_sent_at timestamp for a slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET last_sent_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now(), datetime.now(), slot_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating slot last sent: {e}")
                return False

    async def log_ad_post(self, slot_id: int, destination_id: str, destination_name: str, 
                          worker_id: int, success: bool, error: str = None) -> bool:
        """Log an ad post attempt."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ad_posts (slot_id, destination_id, destination_name, worker_id, success, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (slot_id, destination_id, destination_name, worker_id, success, error))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error logging ad post: {e}")
                return False

    async def get_managed_groups(self, category: str = None) -> List[Dict[str, Any]]:
        """Get managed groups, optionally filtered by category."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if category:
                    cursor.execute('''
                        SELECT * FROM managed_groups 
                        WHERE category = ? AND is_active = 1
                        ORDER BY group_name
                    ''', (category,))
                else:
                    cursor.execute('''
                        SELECT * FROM managed_groups 
                        WHERE is_active = 1
                        ORDER BY category, group_name
                    ''')
                
                groups = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return groups
            except Exception as e:
                self.logger.error(f"Error getting managed groups: {e}")
                return []

    async def add_managed_group(self, group_id: str, group_name: str, category: str) -> bool:
        """Add a managed group."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO managed_groups (group_id, group_name, category)
                    VALUES (?, ?, ?)
                ''', (group_id, group_name, category))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error adding managed group: {e}")
                return False

    async def remove_managed_group(self, group_name: str) -> bool:
        """Remove a managed group."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM managed_groups WHERE group_name = ?
                ''', (group_name,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error removing managed group: {e}")
                return False

    async def activate_subscription(self, user_id: int, tier: str, duration_days: int = 30) -> bool:
        """Activate or extend user subscription."""
        async with self._lock:
            try:
                # Get current subscription
                current_sub = await self.get_user_subscription(user_id)
                
                # Calculate new expiry date
                if current_sub and current_sub['is_active']:
                    # Extend existing subscription
                    current_expiry = datetime.fromisoformat(current_sub['expires'])
                    new_expiry = current_expiry + timedelta(days=duration_days)
                else:
                    # Start new subscription
                    new_expiry = datetime.now() + timedelta(days=duration_days)
                
                # Update subscription
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (tier, new_expiry, datetime.now(), user_id))
                conn.commit()
                conn.close()
                
                self.logger.info(f"✅ Activated {tier} subscription for user {user_id} until {new_expiry}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error activating subscription: {e}")
                return False

    async def close(self):
        """Close database connections."""
        # SQLite doesn't need explicit connection closing
        pass

    async def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    async def create_worker_cooldowns_table(self):
        """Creates the worker_cooldowns table if it doesn't exist."""
        # This table is already created in the initialize method
        pass


    # --- Methods merged from PostgreSQL database ---

    async def _create_tables(self, *args, **kwargs):
        """_create_tables - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method _create_tables not yet implemented for SQLite")
        return None

    async def create_user(self, *args, **kwargs):
        """create_user - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method create_user not yet implemented for SQLite")
        return None

    async def get_user_ad_slots(self, *args, **kwargs):
        """get_user_ad_slots - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_user_ad_slots not yet implemented for SQLite")
        return None

    async def get_or_create_ad_slots(self, *args, **kwargs):
        """get_or_create_ad_slots - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_or_create_ad_slots not yet implemented for SQLite")
        return None

    async def get_ad_slot_by_id(self, *args, **kwargs):
        """get_ad_slot_by_id - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_ad_slot_by_id not yet implemented for SQLite")
        return None

    async def update_ad_slot_content(self, *args, **kwargs):
        """update_ad_slot_content - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method update_ad_slot_content not yet implemented for SQLite")
        return None

    async def update_ad_slot_schedule(self, *args, **kwargs):
        """update_ad_slot_schedule - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method update_ad_slot_schedule not yet implemented for SQLite")
        return None

    async def update_ad_slot_status(self, *args, **kwargs):
        """update_ad_slot_status - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method update_ad_slot_status not yet implemented for SQLite")
        return None

    async def get_destinations_for_slot(self, *args, **kwargs):
        """get_destinations_for_slot - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_destinations_for_slot not yet implemented for SQLite")
        return None

    async def update_destinations_for_slot(self, *args, **kwargs):
        """update_destinations_for_slot - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method update_destinations_for_slot not yet implemented for SQLite")
        return None

    async def get_bot_statistics(self, *args, **kwargs):
        """get_bot_statistics - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_bot_statistics not yet implemented for SQLite")
        return None

    async def update_ad_last_sent(self, *args, **kwargs):
        """update_ad_last_sent - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method update_ad_last_sent not yet implemented for SQLite")
        return None

    async def create_payment(self, *args, **kwargs):
        """create_payment - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method create_payment not yet implemented for SQLite")
        return None

    async def get_expired_subscriptions(self, *args, **kwargs):
        """get_expired_subscriptions - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_expired_subscriptions not yet implemented for SQLite")
        return None

    async def deactivate_expired_subscriptions(self, *args, **kwargs):
        """deactivate_expired_subscriptions - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method deactivate_expired_subscriptions not yet implemented for SQLite")
        return None

    async def get_active_ad_slots(self, *args, **kwargs):
        """get_active_ad_slots - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_active_ad_slots not yet implemented for SQLite")
        return None

    async def get_ad_destinations(self, *args, **kwargs):
        """get_ad_destinations - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_ad_destinations not yet implemented for SQLite")
        return None
