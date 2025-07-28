import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class DatabaseManager:
    """Handle all database operations."""

    def __init__(self, db_path: str, logger):
        self.db_path = db_path
        self.logger = logger
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize database with required tables."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

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

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS destinations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        destination_type TEXT,
                        destination_id TEXT,
                        destination_name TEXT,
                        alias TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        charge_id TEXT UNIQUE,
                        status TEXT,
                        tier TEXT,
                        usd_amount REAL,
                        crypto_currency TEXT,
                        crypto_amount REAL,
                        payment_address TEXT UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS message_stats (
                        user_id INTEGER,
                        date DATE,
                        message_count INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, date),
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                conn.commit()
                conn.close()
                self.logger.info("Database initialized successfully")

            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                raise

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    async def create_or_update_user(self, user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> bool:
        """Create or update user record."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name),
                        updated_at = CURRENT_TIMESTAMP
                ''', (user_id, username, first_name, last_name, username, first_name, last_name))
                conn.commit()
                conn.close()
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
            try:
                expires = datetime.fromisoformat(str(user['subscription_expires']))
                is_active = expires > datetime.now()
            except (ValueError, TypeError):
                expires = None
                is_active = False
        else:
            is_active = False
            expires = None

        return {
            'tier': user['subscription_tier'],
            'expires': str(expires) if expires else None,
            'is_active': is_active
        }

    async def update_subscription(self, user_id: int, tier: str, duration_days: int) -> bool:
        """Update user's subscription."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                expires = datetime.now() + timedelta(days=duration_days)
                cursor.execute('''
                    UPDATE users 
                    SET subscription_tier = ?, subscription_expires = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (tier, expires, user_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating subscription: {e}")
                return False

    async def add_destination(self, user_id: int, dest_type: str, 
                            dest_id: str, dest_name: str) -> bool:
        """Add a forwarding destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO destinations (user_id, destination_type, destination_id, destination_name, alias)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, dest_type, dest_id, dest_name, dest_name))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error adding destination: {e}")
                return False

    async def get_destinations(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's forwarding destinations."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM destinations WHERE user_id = ?"
            params = [user_id]
            if active_only:
                query += " AND is_active = 1"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    async def get_destination_by_id(self, dest_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a single destination by its database ID and user ID."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM destinations WHERE id = ? AND user_id = ?", (dest_id, user_id))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    async def set_destination_alias(self, dest_id: int, user_id: int, alias: str) -> bool:
        """Set a custom alias for a destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE destinations SET alias = ? WHERE id = ? AND user_id = ?", (alias, dest_id, user_id))
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
            except Exception as e:
                self.logger.error(f"Error setting alias: {e}")
                return False

    async def remove_destination(self, user_id: int, dest_id: int) -> bool:
        """Remove a forwarding destination by marking it inactive."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE destinations SET is_active = 0 WHERE user_id = ? AND id = ?", (user_id, dest_id))
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
            except Exception as e:
                self.logger.error(f"Error removing destination: {e}")
                return False

    async def record_payment(self, user_id: int, charge_id: str, tier: str, usd_amount: float,
                           crypto_currency: str, crypto_amount: float, payment_address: str) -> bool:
        """Record a new blockchain payment."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (user_id, charge_id, status, tier, usd_amount, crypto_currency, crypto_amount, payment_address)
                    VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)
                ''', (user_id, charge_id, tier, usd_amount, crypto_currency, crypto_amount, payment_address))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error recording payment: {e}")
                return False

    async def update_payment_status(self, charge_id: str, status: str) -> bool:
        """Update payment status."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if status == 'completed':
                    cursor.execute('''
                        UPDATE payments 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP
                        WHERE charge_id = ?
                    ''', (status, charge_id))
                else:
                    cursor.execute('''
                        UPDATE payments 
                        SET status = ?
                        WHERE charge_id = ?
                    ''', (status, charge_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating payment status: {e}")
                return False

    async def get_pending_payments(self, age_limit_minutes: int) -> List[Dict[str, Any]]:
        """Get pending payments that are not older than the age limit."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            time_limit = datetime.now() - timedelta(minutes=age_limit_minutes)
            cursor.execute("SELECT * FROM payments WHERE status = 'pending' AND created_at > ?", (time_limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    async def get_expiring_subscriptions(self, days_from_now: int) -> List[Dict[str, Any]]:
        """Get subscriptions that will expire on a specific day from now."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            target_date = datetime.now().date() + timedelta(days=days_from_now)
            cursor.execute("""
                SELECT user_id, subscription_tier, subscription_expires
                FROM users
                WHERE date(subscription_expires) = ? AND subscription_expires > ?
            """, (target_date, datetime.now()))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    async def increment_message_count(self, user_id: int) -> bool:
        """Increment user's daily message count."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                today = datetime.now().date()
                cursor.execute('''
                    INSERT INTO message_stats (user_id, date, message_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        message_count = message_count + 1
                ''', (user_id, today))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error incrementing message count: {e}")
                return False

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users from the database."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """Get overall bot statistics."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_expires > datetime('now')")
            active_subs = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(message_count) FROM message_stats WHERE date = date('now')")
            messages_today = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(usd_amount) FROM payments WHERE status = 'completed' AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')")
            revenue_month = cursor.fetchone()[0] or 0

            conn.close()

            return {
                'total_users': total_users,
                'active_subscriptions': active_subs,
                'messages_today': messages_today,
                'revenue_this_month': revenue_month
            }
