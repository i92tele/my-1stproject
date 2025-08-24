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
        self._lock = None

    def _get_lock(self):
        """Get or create the async lock."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

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
        async with self._get_lock():
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
                        amount_usd REAL,
                        crypto_type TEXT,
                        payment_provider TEXT,
                        pay_to_address TEXT,
                        expected_amount_crypto REAL,
                        payment_url TEXT,
                        expires_at TIMESTAMP,
                        attribution_method TEXT DEFAULT 'amount_only',
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

                # Create admin_ad_slots table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admin_ad_slots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_number INTEGER UNIQUE,
                        content TEXT,
                        file_id TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        is_paused BOOLEAN DEFAULT 0,
                        interval_minutes INTEGER DEFAULT 60,
                        last_sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create admin_slot_destinations table
                cursor.execute('''
                            CREATE TABLE IF NOT EXISTS admin_slot_destinations (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                slot_id INTEGER,
                                destination_type TEXT DEFAULT 'group',
                                destination_id TEXT,
                                destination_name TEXT,
                                alias TEXT,
                                is_active BOOLEAN DEFAULT 1,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TEXT
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
            
        async with self._get_lock():
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
            
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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

    async def get_slot_destinations(self, slot_id: int, slot_type: str = 'user') -> List[Dict[str, Any]]:
        """Get destinations for a slot (updated method with slot_type support)."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if slot_type == 'admin':
                    table_name = 'admin_slot_destinations'
                else:
                    table_name = 'slot_destinations'
                
                cursor.execute(f'''
                    SELECT * FROM {table_name}
                    WHERE slot_id = ? AND is_active = 1
                    ORDER BY created_at
                ''', (slot_id,))
                
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting slot destinations: {e}")
                return []

    async def activate_slot(self, slot_id: int) -> bool:
        """Activate a slot."""
        async with self._get_lock():
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
        async with self._get_lock():
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

    async def get_destinations(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Legacy method - get destinations from first slot."""
        slots = await self.get_user_slots(user_id)
        if not slots:
            return []
        
        return await self.get_slot_destinations(slots[0]['id'])

    async def get_destination_by_id(self, dest_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Legacy method - get destination by ID."""
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        """Get all users from the database.
        
        Returns:
            List of user dictionaries
        """
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, 
                           subscription_tier, subscription_expires, 
                           created_at, updated_at
                    FROM users
                    ORDER BY user_id
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                users = []
                for row in rows:
                    users.append({
                        'user_id': row[0],
                        'username': row[1],
                        'first_name': row[2],
                        'last_name': row[3],
                        'subscription_tier': row[4],
                        'subscription_expires': row[5],
                        'created_at': row[6],
                        'updated_at': row[7]
                    })
                
                return users
                
            except Exception as e:
                self.logger.error(f"Error getting all users: {e}")
                return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        async with self._get_lock():
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
        """Get active ad slots that are due for posting (both user and admin slots)."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                all_slots = []
                
                # Get active USER slots that are due for posting (only for users with active subscriptions)
                cursor.execute('''
                    SELECT s.*, u.username, 'user' as slot_type
                    FROM ad_slots s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
                    )
                    ORDER BY s.last_sent_at ASC NULLS FIRST
                ''')
                
                user_slots = [dict(row) for row in cursor.fetchall()]
                all_slots.extend(user_slots)
                
                # Get active ADMIN slots that are due for posting
                cursor.execute('''
                    SELECT s.*, 'admin' as username, 'admin' as slot_type
                    FROM admin_ad_slots s
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
                    )
                    ORDER BY s.last_sent_at ASC NULLS FIRST
                ''')
                
                admin_slots = [dict(row) for row in cursor.fetchall()]
                all_slots.extend(admin_slots)
                
                # Sort all slots by last_sent_at (NULL first, then by time)
                all_slots.sort(key=lambda x: (x['last_sent_at'] is not None, x['last_sent_at'] or ''))
                
                conn.close()
                return all_slots
                
            except Exception as e:
                self.logger.error(f"Error getting active ads to send: {e}")
                return []

    async def update_slot_last_sent(self, slot_id: int, slot_type: str = 'user') -> bool:
        """Update the last_sent_at timestamp for a slot (user or admin)."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Format datetime as string for SQLite storage
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if slot_type == 'admin':
                    cursor.execute('''
                        UPDATE admin_ad_slots 
                        SET last_sent_at = ?, updated_at = ?
                        WHERE id = ?
                    ''', (current_time, current_time, slot_id))
                else:
                    cursor.execute('''
                        UPDATE ad_slots 
                        SET last_sent_at = ?, updated_at = ?
                        WHERE id = ?
                    ''', (current_time, current_time, slot_id))
                
                conn.commit()
                conn.close()
                self.logger.info(f"✅ Updated last_sent_at for {slot_type} slot {slot_id} to {current_time}")
                return True
            except Exception as e:
                self.logger.error(f"Error updating slot last sent: {e}")
                return False

    async def log_ad_post(self, slot_id: int, destination_id: str, destination_name: str, 
                          worker_id: int, success: bool, error: str = None) -> bool:
        """Log an ad post attempt."""
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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
        async with self._get_lock():
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

    async def create_payment(self, payment_id: str, user_id: int, amount_usd: float, 
                              crypto_type: str, payment_provider: str, pay_to_address: str,
                              expected_amount_crypto: float, payment_url: str, expires_at: datetime,
                              attribution_method: str = 'amount_only') -> bool:
        """Create a new payment record in the database."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "INSERT INTO payments (payment_id, user_id, amount_usd, crypto_type, payment_provider, pay_to_address, expected_amount_crypto, payment_url, expires_at, attribution_method, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)"
                cursor.execute(query, (payment_id, user_id, amount_usd, crypto_type, payment_provider, pay_to_address, expected_amount_crypto, payment_url, expires_at.isoformat(), attribution_method, datetime.now(), datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"✅ Created payment {payment_id} for user {user_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error creating payment {payment_id}: {e}")
                return False

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

    async def initialize_worker_limits(self, worker_id: int) -> bool:
        """Initialize worker limits for a new worker."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Initialize in worker_usage table
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_usage 
                    (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, created_at)
                    VALUES (?, 0, 0, 15, 150, ?)
                ''', (worker_id, datetime.now()))
                
                # Note: worker_cooldowns table is created separately and doesn't need initialization
                # Cooldowns are set dynamically when workers are used
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Initialized limits for worker {worker_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error initializing worker limits for {worker_id}: {e}")
                return False

    async def get_worker_bans(self, worker_id: int = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get worker ban information."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Handle missing worker_health table gracefully
                try:
                    if worker_id:
                        cursor.execute('''
                            SELECT worker_id, ban_count, last_ban_date, is_banned
                            FROM worker_health WHERE worker_id = ?
                        ''', (worker_id,))
                    else:
                        cursor.execute('''
                            SELECT worker_id, ban_count, last_ban_date, is_banned
                            FROM worker_health
                        ''')
                    rows = cursor.fetchall()
                except sqlite3.OperationalError:
                    # Table doesn't exist or columns missing
                    rows = []
                conn.close()
                
                return [
                    {
                        'worker_id': row[0],
                        'ban_count': row[1],
                        'last_ban_date': row[2],
                        'is_banned': bool(row[3])
                    }
                    for row in rows
                ]
                
            except Exception as e:
                self.logger.error(f"Error getting worker bans: {e}")
                return []

    async def get_recent_posting_activity(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent posting activity for recovery analysis."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT slot_id, worker_id, destination_id, posted_at, success
                    FROM posting_history 
                    WHERE posted_at > datetime('now', '-{} hours')
                    ORDER BY posted_at DESC
                '''.format(hours))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [
                    {
                        'slot_id': row[0],
                        'worker_id': row[1],
                        'destination_id': row[2],
                        'posted_at': row[3],
                        'success': bool(row[4])
                    }
                    for row in rows
                ]
                
            except Exception as e:
                self.logger.error(f"Error getting recent posting activity: {e}")
                return []

    async def get_destination_health_summary(self) -> Dict[str, Any]:
        """Get destination health summary for recovery."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT destination_id, success_rate, last_success, last_failure, total_attempts
                    FROM destination_health
                    ORDER BY success_rate DESC
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                return {
                    'destinations': [
                        {
                            'destination_id': row[0],
                            'success_rate': row[1],
                            'last_success': row[2],
                            'last_failure': row[3],
                            'total_attempts': row[4]
                        }
                        for row in rows
                    ],
                    'total_destinations': len(rows)
                }
                
            except Exception as e:
                self.logger.error(f"Error getting destination health summary: {e}")
                return {'destinations': [], 'total_destinations': 0}

    async def get_worker_usage(self, worker_id: int) -> Dict[str, Any]:
        """Get worker usage statistics."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get basic usage stats - handle missing columns gracefully
                try:
                    cursor.execute('''
                        SELECT 
                            daily_limit,
                            hourly_limit,
                            messages_sent_today,
                            messages_sent_this_hour
                        FROM worker_usage 
                        WHERE worker_id = ?
                    ''', (worker_id,))
                    result = cursor.fetchone()
                except sqlite3.OperationalError:
                    # Table or columns don't exist, return defaults
                    result = None
                if result:
                    usage = dict(result)
                    usage['daily_percentage'] = (usage['messages_sent_today'] / usage['daily_limit']) * 100 if usage['daily_limit'] > 0 else 0
                    usage['hourly_percentage'] = (usage['messages_sent_this_hour'] / usage['hourly_limit']) * 100 if usage['hourly_limit'] > 0 else 0
                else:
                    usage = {
                        'daily_limit': 50,
                        'hourly_limit': 20,
                        'messages_sent_today': 0,
                        'messages_sent_this_hour': 0,
                        'daily_percentage': 0,
                        'hourly_percentage': 0
                    }
                
                conn.close()
                return usage
                
            except Exception as e:
                self.logger.error(f"Error getting worker usage: {e}")
                return {
                    'daily_limit': 50,
                    'hourly_limit': 20,
                    'messages_sent_today': 0,
                    'messages_sent_this_hour': 0,
                    'daily_percentage': 0,
                    'hourly_percentage': 0
                }



    async def get_posting_history(self, worker_id: int = None, hours: int = 24, limit: int = None) -> List[Dict[str, Any]]:
        """Get posting history."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if worker_id:
                    cursor.execute('''
                        SELECT * FROM worker_activity_log
                        WHERE worker_id = ? 
                        AND created_at > datetime('now', '-' || ? || ' hours')
                        ORDER BY created_at DESC
                    ''', (worker_id, hours))
                else:
                    cursor.execute('''
                        SELECT * FROM worker_activity_log
                        WHERE created_at > datetime('now', '-' || ? || ' hours')
                        ORDER BY created_at DESC
                    ''', (hours,))
                
                history = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return history
                
            except Exception as e:
                self.logger.error(f"Error getting posting history: {e}")
                return []

    async def get_problematic_destinations(self, min_failures: int = 3) -> List[Dict[str, Any]]:
        """Get destinations with issues."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # This is a placeholder - implement actual logic to identify problematic destinations
                cursor.execute('''
                    SELECT destination_id, destination_name, 
                           COUNT(*) as error_count
                    FROM worker_activity_log
                    WHERE success = 0 
                    AND created_at > datetime('now', '-24 hours')
                    GROUP BY destination_id, destination_name
                    HAVING error_count > ?
                    ORDER BY error_count DESC
                ''', (min_failures,))
                
                problematic = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return problematic
                
            except Exception as e:
                self.logger.error(f"Error getting problematic destinations: {e}")
                return []

    async def record_failed_group_join(self, worker_id: int, group_id: str, error: str) -> bool:
        """Record a failed group join attempt."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO failed_group_joins (worker_id, group_id, error, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (worker_id, group_id, error, datetime.now()))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error recording failed group join: {e}")
                return False

    async def record_worker_ban(self, worker_id: int, destination_id: str, ban_type: str, ban_reason: str, estimated_unban_time: str = None) -> bool:
        """Record a worker ban for a specific destination."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if worker_bans table exists with the right columns, create/alter if not
                try:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS worker_bans (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            worker_id INTEGER,
                            destination_id TEXT,
                            ban_type TEXT,
                            ban_reason TEXT,
                            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            estimated_unban_time TIMESTAMP,
                            is_active BOOLEAN DEFAULT 1
                        )
                    ''')
                except sqlite3.OperationalError as e:
                    self.logger.warning(f"Error checking/creating worker_bans table: {e}")
                
                # Insert ban record
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO worker_bans 
                    (worker_id, destination_id, ban_type, ban_reason, banned_at, estimated_unban_time, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (worker_id, destination_id, ban_type, ban_reason, now, estimated_unban_time))
                
                conn.commit()
                conn.close()
                self.logger.info(f"Recorded ban for worker {worker_id} in {destination_id}: {ban_type}")
                return True
            except Exception as e:
                self.logger.error(f"Error recording worker ban: {e}")
                return False
                
    async def is_worker_banned(self, worker_id: int, group_id: str = None) -> bool:
        """Check if worker is banned."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if group_id:
                    cursor.execute('''
                        SELECT COUNT(*) FROM worker_bans 
                        WHERE worker_id = ? AND chat_id = ?
                    ''', (worker_id, group_id))
                else:
                    cursor.execute('''
                        SELECT COUNT(*) FROM worker_bans 
                        WHERE worker_id = ?
                    ''', (worker_id,))
                
                count = cursor.fetchone()[0]
                conn.close()
                return count > 0
            except Exception as e:
                self.logger.error(f"Error checking worker ban: {e}")
                return False

    async def record_posting_attempt(self, worker_id: int, group_id: str, success: bool, error: str = None) -> bool:
        """Record a posting attempt."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO worker_activity_log (worker_id, chat_id, success, error, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (worker_id, group_id, success, error, datetime.now()))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error recording posting attempt: {e}")
                return False

    async def update_destination_health(self, destination_id: str, success: bool) -> bool:
        """Update destination health stats."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # This is a simple implementation - you might want to enhance this
                current_time = datetime.now()
                if success:
                    cursor.execute('''
                        UPDATE destination_health 
                        SET last_success = ?, total_attempts = total_attempts + 1
                        WHERE destination_id = ?
                    ''', (current_time, destination_id))
                else:
                    cursor.execute('''
                        UPDATE destination_health 
                        SET last_failure = ?, total_attempts = total_attempts + 1
                        WHERE destination_id = ?
                    ''', (current_time, destination_id))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating destination health: {e}")
                return False

    async def record_worker_post(self, worker_id: int, destination_id: str) -> bool:
        """Record worker post for usage tracking."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                today = datetime.now().date()
                current_hour = datetime.now().hour
                
                # Try to update existing record
                cursor.execute('''
                    UPDATE worker_usage 
                    SET messages_sent_today = messages_sent_today + 1,
                        messages_sent_this_hour = CASE 
                            WHEN last_reset_hour = ? THEN messages_sent_this_hour + 1
                            ELSE 1
                        END,
                        last_reset_hour = ?,
                        updated_at = ?
                    WHERE worker_id = ? AND date = ?
                ''', (current_hour, current_hour, datetime.now(), worker_id, today))
                
                if cursor.rowcount == 0:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO worker_usage (worker_id, date, messages_sent_today, messages_sent_this_hour, last_reset_hour, created_at)
                        VALUES (?, ?, 1, 1, ?, ?)
                    ''', (worker_id, today, current_hour, datetime.now()))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error recording worker post: {e}")
                return False

    async def get_admin_ad_slots(self) -> List[Dict[str, Any]]:
        """Get all admin ad slots."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM admin_ad_slots 
                    ORDER BY id
                ''')
                
                slots = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return slots
                
            except Exception as e:
                self.logger.error(f"Error getting admin ad slots: {e}")
                return []

    async def get_admin_ad_slot(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot by slot number."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM admin_ad_slots 
                    WHERE slot_number = ?
                ''', (slot_number,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return dict(row)
                else:
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error getting admin ad slot {slot_number}: {e}")
                return None

    async def get_admin_slot_destinations(self, slot_number: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific admin ad slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # First get the slot_id from admin_ad_slots using slot_number
                cursor.execute('''
                    SELECT id FROM admin_ad_slots 
                    WHERE slot_number = ?
                ''', (slot_number,))
                
                slot_row = cursor.fetchone()
                if not slot_row:
                    conn.close()
                    return []
                
                slot_id = slot_row[0]
                
                # Then get destinations using the slot_id
                cursor.execute('''
                    SELECT * FROM admin_slot_destinations 
                    WHERE slot_id = ? AND is_active = 1
                    ORDER BY id
                ''', (slot_id,))
                
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting admin slot destinations for slot {slot_number}: {e}")
                return []

    async def update_admin_slot_content(self, slot_number: int, content: str, file_id: str = None) -> bool:
        """Update content for a specific admin ad slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if file_id:
                    cursor.execute('''
                        UPDATE admin_ad_slots 
                        SET content = ?, file_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE slot_number = ?
                    ''', (content, file_id, slot_number))
                else:
                    cursor.execute('''
                        UPDATE admin_ad_slots 
                        SET content = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE slot_number = ?
                    ''', (content, slot_number))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated admin slot {slot_number} content")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot {slot_number} content: {e}")
                return False

    async def update_admin_slot_status(self, slot_number: int, is_active: bool) -> bool:
        """Update status for a specific admin ad slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE admin_ad_slots 
                    SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE slot_number = ?
                ''', (is_active, slot_number))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated admin slot {slot_number} status to {is_active}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot {slot_number} status: {e}")
                return False

    async def update_admin_slot_destinations(self, slot_number: int, destinations: List[Dict[str, Any]]) -> bool:
        """Update destinations for an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get slot_id from slot_number
                cursor.execute('SELECT id FROM admin_ad_slots WHERE slot_number = ?', (slot_number,))
                slot_row = cursor.fetchone()
                if not slot_row:
                    conn.close()
                    return False
                
                slot_id = slot_row[0]
                
                # Delete existing destinations
                cursor.execute('DELETE FROM admin_slot_destinations WHERE slot_id = ?', (slot_id,))
                
                # Insert new destinations
                for dest in destinations:
                    cursor.execute('''
                        INSERT INTO admin_slot_destinations 
                        (slot_id, destination_type, destination_id, destination_name, alias, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    ''', (
                        slot_id,
                        dest.get('destination_type', 'group'),
                        dest.get('destination_id', ''),
                        dest.get('destination_name', ''),
                        dest.get('alias', ''),
                        dest.get('is_active', True),
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated admin slot {slot_number} destinations ({len(destinations)} destinations)")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating admin slot {slot_number} destinations: {e}")
                return False

    async def add_admin_slot_destination(self, slot_number: int, destination_data: Dict[str, Any]) -> bool:
        """Add a single destination to an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get slot_id from slot_number
                cursor.execute('SELECT id FROM admin_ad_slots WHERE slot_number = ?', (slot_number,))
                slot_row = cursor.fetchone()
                if not slot_row:
                    conn.close()
                    return False
                
                slot_id = slot_row[0]
                
                # Check if destination already exists
                cursor.execute('''
                    SELECT id FROM admin_slot_destinations 
                    WHERE slot_id = ? AND destination_id = ?
                ''', (slot_id, destination_data.get('destination_id', '')))
                
                if cursor.fetchone():
                    # Destination already exists
                    conn.close()
                    return True
                
                # Insert new destination
                cursor.execute('''
                    INSERT INTO admin_slot_destinations 
                    (slot_id, destination_type, destination_id, destination_name, alias, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (
                    slot_id,
                    destination_data.get('destination_type', 'group'),
                    destination_data.get('destination_id', ''),
                    destination_data.get('destination_name', ''),
                    destination_data.get('alias', ''),
                    destination_data.get('is_active', True),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Added destination to admin slot {slot_number}: {destination_data.get('destination_name', 'Unknown')}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error adding destination to admin slot {slot_number}: {e}")
                return False

    async def remove_admin_slot_destination(self, slot_number: int, destination_id: str) -> bool:
        """Remove a single destination from an admin slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get slot_id from slot_number
                cursor.execute('SELECT id FROM admin_ad_slots WHERE slot_number = ?', (slot_number,))
                slot_row = cursor.fetchone()
                if not slot_row:
                    conn.close()
                    return False
                
                slot_id = slot_row[0]
                
                # Delete the destination
                cursor.execute('''
                    DELETE FROM admin_slot_destinations 
                    WHERE slot_id = ? AND destination_id = ?
                ''', (slot_id, destination_id))
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted_count > 0:
                    self.logger.info(f"Removed destination from admin slot {slot_number}: {destination_id}")
                    return True
                else:
                    self.logger.warning(f"Destination not found in admin slot {slot_number}: {destination_id}")
                    return False
                
            except Exception as e:
                self.logger.error(f"Error removing destination from admin slot {slot_number}: {e}")
                return False

    async def delete_admin_slot(self, slot_number: int) -> bool:
        """Delete a specific admin ad slot."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Delete the slot
                cursor.execute('DELETE FROM admin_ad_slots WHERE slot_number = ?', (slot_number,))
                
                # Delete associated destinations
                cursor.execute('DELETE FROM admin_slot_destinations WHERE slot_id = (SELECT id FROM admin_ad_slots WHERE slot_number = ?)', (slot_number,))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Deleted admin slot {slot_number}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting admin slot {slot_number}: {e}")
                return False

    async def create_admin_ad_slots(self) -> bool:
        """Create initial admin ad slots if none exist."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if admin slots already exist
                cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    self.logger.info(f"Admin slots already exist ({existing_count} slots)")
                    conn.close()
                    return True
                
                # Create 5 initial admin slots
                sample_content = [
                    "🚀 Welcome to AutoFarming Pro! Promote your services automatically.",
                    "📈 Boost your business with automated posting to premium groups.",
                    "💎 Premium advertising slots for maximum visibility.",
                    "🎯 Targeted promotion to high-quality Telegram groups.",
                    "⚡ Lightning-fast automated posting service."
                ]
                
                for i in range(1, 6):
                    cursor.execute('''
                        INSERT INTO admin_ad_slots (slot_number, content, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (i, sample_content[i-1], True, datetime.now(), datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info("Created 5 initial admin ad slots")
                return True
                
            except Exception as e:
                self.logger.error(f"Error creating admin ad slots: {e}")
                return False

    async def get_all_workers(self) -> List[Dict[str, Any]]:
        """Get all workers from the database."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get workers from worker_cooldowns table with any available stats
                cursor.execute('''
                    SELECT 
                        wc.worker_id,
                        wc.is_active,
                        wc.last_used_at,
                        wc.created_at,
                        COALESCE(wu.messages_sent_today, 0) as messages_today,
                        COALESCE(wu.daily_limit, 50) as daily_limit
                    FROM worker_cooldowns wc
                    LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                        AND wu.date = date('now')
                    ORDER BY wc.worker_id
                ''')
                
                workers = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return workers
                
            except Exception as e:
                self.logger.error(f"Error getting all workers: {e}")
                return []

    async def get_available_workers(self) -> List[Dict[str, Any]]:
        """Get available (active and not at limit) workers."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        wc.worker_id,
                        wc.is_active,
                        wc.last_used_at,
                        COALESCE(wu.messages_sent_today, 0) as messages_today,
                        COALESCE(wu.daily_limit, 50) as daily_limit
                    FROM worker_cooldowns wc
                    LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                        AND wu.date = date('now')
                    WHERE wc.is_active = 1 
                    AND COALESCE(wu.messages_sent_today, 0) < COALESCE(wu.daily_limit, 50)
                    ORDER BY wc.last_used_at ASC NULLS FIRST
                ''')
                
                workers = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return workers
                
            except Exception as e:
                self.logger.error(f"Error getting available workers: {e}")
                return []

    async def get_managed_group_category_counts(self) -> Dict[str, int]:
        """Get count of managed groups by category."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM managed_groups 
                    WHERE is_active = 1 
                    GROUP BY category
                    ORDER BY category
                ''')
                
                counts = {}
                for row in cursor.fetchall():
                    counts[row[0]] = row[1]
                
                conn.close()
                return counts
                
            except Exception as e:
                self.logger.error(f"Error getting group category counts: {e}")
                return {}

    async def get_failed_group_joins(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed group join attempts."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM failed_group_joins 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                failed_joins = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return failed_joins
                
            except Exception as e:
                self.logger.error(f"Error getting failed group joins: {e}")
                return []

    async def get_admin_slots_stats(self) -> Dict[str, Any]:
        """Get admin slot statistics."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Total admin slots
                cursor.execute('SELECT COUNT(*) FROM admin_ad_slots')
                total_slots = cursor.fetchone()[0]
                
                # Active admin slots
                cursor.execute('SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1')
                active_slots = cursor.fetchone()[0]
                
                # Paused admin slots
                cursor.execute('SELECT COUNT(*) FROM admin_ad_slots WHERE is_paused = 1')
                paused_slots = cursor.fetchone()[0]
                
                conn.close()
                return {
                    'total_slots': total_slots,
                    'active_slots': active_slots,
                    'paused_slots': paused_slots
                }
                
            except Exception as e:
                self.logger.error(f"Error getting admin slots stats: {e}")
                return {
                    'total_slots': 0,
                    'active_slots': 0,
                    'paused_slots': 0
                }

    async def get_revenue_stats(self) -> Dict[str, Any]:
        """Get revenue statistics from payments."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if payments table exists and get basic stats
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_payments,
                        COALESCE(SUM(amount), 0) as total_revenue,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_payments,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
                        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_payments
                    FROM payments
                ''')
                stats = cursor.fetchone()
                
                # Get recent revenue (last 7 days)
                cursor.execute('''
                    SELECT 
                        COUNT(*) as recent_count,
                        COALESCE(SUM(amount), 0) as recent_revenue
                    FROM payments 
                    WHERE status = 'completed' 
                    AND created_at >= datetime('now', '-7 days')
                ''')
                recent_stats = cursor.fetchone()
                
                # Try to get crypto breakdown (will fail gracefully if column doesn't exist)
                crypto_stats = []
                try:
                    cursor.execute('''
                        SELECT 
                            COALESCE(crypto_type, currency, 'Unknown') as crypto,
                            COUNT(*) as count,
                            COALESCE(SUM(amount), 0) as revenue
                        FROM payments 
                        WHERE status = 'completed'
                        GROUP BY COALESCE(crypto_type, currency)
                        ORDER BY revenue DESC
                    ''')
                    crypto_stats = cursor.fetchall()
                except sqlite3.OperationalError:
                    # crypto_type column doesn't exist, fall back to currency
                    try:
                        cursor.execute('''
                            SELECT 
                                currency,
                                COUNT(*) as count,
                                COALESCE(SUM(amount), 0) as revenue
                            FROM payments 
                            WHERE status = 'completed'
                            GROUP BY currency
                            ORDER BY revenue DESC
                        ''')
                        crypto_stats = cursor.fetchall()
                    except sqlite3.OperationalError:
                        # Neither column exists
                        crypto_stats = []
                
                conn.close()
                
                return {
                    'total_payments': stats[0] if stats else 0,
                    'total_revenue': stats[1] if stats else 0,
                    'completed_payments': stats[2] if stats else 0,
                    'pending_payments': stats[3] if stats else 0,
                    'cancelled_payments': stats[4] if stats else 0,
                    'recent_count': recent_stats[0] if recent_stats else 0,
                    'recent_revenue': recent_stats[1] if recent_stats else 0,
                    'crypto_breakdown': crypto_stats
                }
                
            except Exception as e:
                self.logger.error(f"Error getting revenue stats: {e}")
                return {
                    'total_payments': 0,
                    'total_revenue': 0,
                    'completed_payments': 0,
                    'pending_payments': 0,
                    'cancelled_payments': 0,
                    'recent_count': 0,
                    'recent_revenue': 0,
                    'crypto_breakdown': []
                }

    async def ensure_worker_cooldowns_table(self):
        """Ensure worker_cooldowns table exists."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_cooldowns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER NOT NULL,
                        cooldown_until TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now')),
                        FOREIGN KEY (worker_id) REFERENCES worker_usage (worker_id)
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_worker_cooldowns_worker_id 
                    ON worker_cooldowns (worker_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_worker_cooldowns_until 
                    ON worker_cooldowns (cooldown_until)
                ''')
                
                conn.commit()
                conn.close()
                self.logger.info("✅ worker_cooldowns table ensured")
                
            except Exception as e:
                self.logger.error(f"Error ensuring worker_cooldowns table: {e}")


    async def get_paused_slots(self) -> List[Dict[str, Any]]:
        """Get all paused ad slots for monitoring."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.*, u.username, u.first_name 
                    FROM ad_slots s 
                    JOIN users u ON s.user_id = u.user_id 
                    WHERE s.is_paused = 1 
                    ORDER BY s.pause_time DESC
                ''')
                slots = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return slots
            except Exception as e:
                self.logger.error(f"Error getting paused slots: {e}")
                return []
    async def get_failed_groups(self) -> List[Dict[str, Any]]:
        """Get failed group joins for admin monitoring."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM failed_group_joins ORDER BY failed_at DESC LIMIT 50")
                groups = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return groups
            except Exception as e:
                self.logger.error(f"Error getting failed groups: {e}")
                return []


    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status for admin monitoring."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
                active_slots = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM worker_usage")
                total_workers = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
                active_subscriptions = cursor.fetchone()[0]
                conn.close()
                return {'total_users': total_users, 'active_slots': active_slots, 'total_workers': total_workers, 'active_subscriptions': active_subscriptions, 'system_status': 'operational'}
            except Exception as e:
                self.logger.error(f"Error getting system status: {e}")
                return {'system_status': 'error', 'error': str(e)}

    async def get_ad_slots(self) -> List[Dict[str, Any]]:
        """Get all ad slots from the database.
        
        Returns:
            List of ad slot dictionaries
        """
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, user_id, slot_number, content, file_id, 
                           is_active, interval_minutes, last_sent_at, created_at
                    FROM ad_slots
                    ORDER BY user_id, slot_number
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                ad_slots = []
                for row in rows:
                    ad_slots.append({
                        'id': row[0],
                        'user_id': row[1],
                        'slot_number': row[2],
                        'content': row[3],
                        'file_id': row[4],
                        'is_active': bool(row[5]),
                        'interval_minutes': row[6],
                        'last_sent_at': row[7],
                        'created_at': row[8]
                    })
                
                return ad_slots
                
            except Exception as e:
                self.logger.error(f"Error getting ad slots: {e}")
                return []

    async def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all user subscriptions from the database.
        
        Returns:
            List of subscription dictionaries
        """
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, subscription_tier, subscription_expires, 
                           created_at, updated_at
                    FROM users
                    WHERE subscription_tier IS NOT NULL
                    ORDER BY user_id
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                subscriptions = []
                for row in rows:
                    subscriptions.append({
                        'user_id': row[0],
                        'tier': row[1],
                        'expires': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
                
                return subscriptions
                
            except Exception as e:
                self.logger.error(f"Error getting all subscriptions: {e}")
                return []

    async def get_all_payments(self) -> List[Dict[str, Any]]:
        """Get all payments from the database.
        
        Returns:
            List of payment dictionaries
        """
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, payment_id, user_id, tier, amount_usd, 
                           amount_crypto, crypto_type, status, created_at
                    FROM payments
                    ORDER BY created_at DESC
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                payments = []
                for row in rows:
                    payments.append({
                        'id': row[0],
                        'payment_id': row[1],
                        'user_id': row[2],
                        'tier': row[3],
                        'amount_usd': row[4],
                        'amount_crypto': row[5],
                        'crypto_type': row[6],
                        'status': row[7],
                        'created_at': row[8]
                    })
                
                return payments
                
            except Exception as e:
                self.logger.error(f"Error getting all payments: {e}")
                return []

    async def delete_user_and_data(self, user_id: int) -> bool:
        """Delete a user and all related data (ad slots, destinations, payments, stats, posts).

        Order of operations avoids FK issues:
        - Find slot ids -> delete slot_destinations, ad_posts
        - Delete ad_slots
        - Delete payments, message_stats
        - Delete user
        """
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                cursor = conn.cursor()
                
                # Collect slot ids
                cursor.execute("SELECT id FROM ad_slots WHERE user_id = ?", (user_id,))
                slot_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete per-slot data
                if slot_ids:
                    cursor.execute(
                        f"DELETE FROM slot_destinations WHERE slot_id IN ({','.join(['?']*len(slot_ids))})",
                        slot_ids,
                    )
                    cursor.execute(
                        f"DELETE FROM ad_posts WHERE slot_id IN ({','.join(['?']*len(slot_ids))})",
                        slot_ids,
                    )
                
                # Delete ad slots
                cursor.execute("DELETE FROM ad_slots WHERE user_id = ?", (user_id,))
                
                # Delete payments and stats
                cursor.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM message_stats WHERE user_id = ?", (user_id,))
                
                # Finally delete user
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                
                conn.commit()
                conn.close()
                self.logger.info(f"Deleted user {user_id} and associated data")
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting user {user_id}: {e}")
                return False



