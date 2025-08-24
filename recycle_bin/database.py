import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import math

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
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA cache_size=10000;")
                conn.execute("PRAGMA temp_store=MEMORY;")
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
                        category TEXT DEFAULT 'general',
                        assigned_worker_id INTEGER DEFAULT 1,
                        is_active BOOLEAN DEFAULT 0,
                        is_paused BOOLEAN DEFAULT 0,
                        pause_reason TEXT,
                        pause_time TIMESTAMP,
                        interval_minutes INTEGER DEFAULT 60,
                        last_sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Lightweight schema migration to add missing columns if DB already existed
                try:
                    cursor.execute("PRAGMA table_info(ad_slots)")
                    existing_cols = {row[1] for row in cursor.fetchall()}
                    alter_statements = []
                    if 'category' not in existing_cols:
                        alter_statements.append("ALTER TABLE ad_slots ADD COLUMN category TEXT DEFAULT 'general'")
                    if 'assigned_worker_id' not in existing_cols:
                        alter_statements.append("ALTER TABLE ad_slots ADD COLUMN assigned_worker_id INTEGER DEFAULT 1")
                    if 'is_active' not in existing_cols:
                        alter_statements.append("ALTER TABLE ad_slots ADD COLUMN is_active BOOLEAN DEFAULT 0")
                    if 'interval_minutes' not in existing_cols:
                        alter_statements.append("ALTER TABLE ad_slots ADD COLUMN interval_minutes INTEGER DEFAULT 60")
                    if 'last_sent_at' not in existing_cols:
                        alter_statements.append("ALTER TABLE ad_slots ADD COLUMN last_sent_at TIMESTAMP")
                    if 'updated_at' not in existing_cols:
                        # SQLite can't add a column with a non-constant default via ALTER.
                        # Add without default, then backfill values.
                        try:
                            cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TIMESTAMP")
                            # Backfill existing rows
                            cursor.execute("UPDATE ad_slots SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
                        except Exception as mig_e:
                            self.logger.warning(f"Schema migration for updated_at failed: {mig_e}")
                    for stmt in alter_statements:
                        try:
                            cursor.execute(stmt)
                        except Exception as mig_e:
                            self.logger.warning(f"Schema migration skipped: {stmt} -> {mig_e}")
                except Exception as e:
                    self.logger.warning(f"Could not run ad_slots schema migration: {e}")

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
                        requires_manual BOOLEAN DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        last_error_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (slot_id) REFERENCES ad_slots(id)
                    )
                ''')

                # Migrate slot_destinations for new columns
                try:
                    cursor.execute("PRAGMA table_info(slot_destinations)")
                    sd_cols = {row[1] for row in cursor.fetchall()}
                    if 'requires_manual' not in sd_cols:
                        cursor.execute("ALTER TABLE slot_destinations ADD COLUMN requires_manual BOOLEAN DEFAULT 0")
                    if 'failure_count' not in sd_cols:
                        cursor.execute("ALTER TABLE slot_destinations ADD COLUMN failure_count INTEGER DEFAULT 0")
                    if 'last_error' not in sd_cols:
                        cursor.execute("ALTER TABLE slot_destinations ADD COLUMN last_error TEXT")
                    if 'last_error_at' not in sd_cols:
                        cursor.execute("ALTER TABLE slot_destinations ADD COLUMN last_error_at TIMESTAMP")
                except Exception as sd_mig_err:
                    self.logger.warning(f"slot_destinations migration skipped: {sd_mig_err}")

                # Create payments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payment_id TEXT UNIQUE,
                        user_id INTEGER,
                        amount REAL,
                        currency TEXT,
                        crypto_type TEXT DEFAULT 'TON',
                        status TEXT,
                        payment_provider TEXT DEFAULT 'direct',
                        provider_payment_id TEXT,
                        -- Extended fields for direct/self-custody invoices
                        expected_amount_crypto REAL,
                        pay_to_address TEXT,
                        network TEXT,
                        required_confirmations INTEGER,
                        detected_tx_hash TEXT,
                        detected_at TIMESTAMP,
                        confirmed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        timeout_minutes INTEGER,
                        updated_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Migrate payments table for new columns (idempotent)
                try:
                    cursor.execute("PRAGMA table_info(payments)")
                    p_cols = {row[1] for row in cursor.fetchall()}
                    if 'expected_amount_crypto' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN expected_amount_crypto REAL")
                    if 'pay_to_address' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN pay_to_address TEXT")
                    if 'network' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN network TEXT")
                    if 'required_confirmations' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN required_confirmations INTEGER")
                    if 'detected_tx_hash' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN detected_tx_hash TEXT")
                    if 'detected_at' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN detected_at TIMESTAMP")
                    if 'confirmed_at' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN confirmed_at TIMESTAMP")
                    if 'provider_payment_id' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN provider_payment_id TEXT")
                    if 'crypto_type' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN crypto_type TEXT DEFAULT 'TON'")
                    if 'payment_provider' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN payment_provider TEXT DEFAULT 'direct'")
                    if 'attribution_method' not in p_cols:
                        cursor.execute("ALTER TABLE payments ADD COLUMN attribution_method TEXT DEFAULT 'amount_only'")
                    # Helpful indices
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_expires ON payments(expires_at)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider_payment_id)")
                except Exception as pay_mig_err:
                    self.logger.warning(f"payments migration skipped: {pay_mig_err}")

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

                # Create/migrate worker_usage table (hourly and daily)
                try:
                    # Check if table exists and has correct structure
                    cursor.execute("PRAGMA table_info(worker_usage)")
                    existing_cols = {row[1]: row[2] for row in cursor.fetchall()}
                    
                    # If table exists but missing required columns, recreate it
                    if existing_cols and ('hourly_posts' not in existing_cols or 'daily_posts' not in existing_cols):
                        self.logger.info("Recreating worker_usage table with correct schema...")
                        cursor.execute("DROP TABLE IF EXISTS worker_usage")
                        
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS worker_usage (
                            worker_id INTEGER,
                            hour TEXT,
                            hourly_posts INTEGER DEFAULT 0,
                            daily_posts INTEGER DEFAULT 0,
                            day TEXT,
                            PRIMARY KEY (worker_id, hour)
                        )
                    ''')
                except Exception as wu_err:
                    self.logger.warning(f"worker_usage table creation failed: {wu_err}")

                # Create/migrate worker_health table
                try:
                    # Check if table exists and has correct structure
                    cursor.execute("PRAGMA table_info(worker_health)")
                    existing_cols = {row[1]: row[2] for row in cursor.fetchall()}
                    
                    # If table exists but missing required columns, recreate it
                    if existing_cols and ('successful_posts' not in existing_cols or 'total_posts' not in existing_cols):
                        self.logger.info("Recreating worker_health table with correct schema...")
                        cursor.execute("DROP TABLE IF EXISTS worker_health")
                        
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS worker_health (
                            worker_id INTEGER PRIMARY KEY,
                            successful_posts INTEGER DEFAULT 0,
                            total_posts INTEGER DEFAULT 0,
                            success_rate REAL DEFAULT 100.0,
                            error_count INTEGER DEFAULT 0,
                            ban_count INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                except Exception as wh_err:
                    self.logger.warning(f"worker_health table creation failed: {wh_err}")

                # Add ban_count column to existing worker_health table if it doesn't exist
                try:
                    cursor.execute("PRAGMA table_info(worker_health)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'ban_count' not in columns:
                        self.logger.info("Adding ban_count column to worker_health table...")
                        cursor.execute("ALTER TABLE worker_health ADD COLUMN ban_count INTEGER DEFAULT 0")
                        conn.commit()
                        self.logger.info("ban_count column added successfully")
                except Exception as ban_mig_err:
                    self.logger.warning(f"ban_count migration failed: {ban_mig_err}")

                # Add pause columns to existing ad_slots table if they don't exist
                try:
                    cursor.execute("PRAGMA table_info(ad_slots)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'is_paused' not in columns:
                        self.logger.info("Adding pause columns to ad_slots table...")
                        cursor.execute("ALTER TABLE ad_slots ADD COLUMN is_paused BOOLEAN DEFAULT 0")
                        cursor.execute("ALTER TABLE ad_slots ADD COLUMN pause_reason TEXT")
                        cursor.execute("ALTER TABLE ad_slots ADD COLUMN pause_time TIMESTAMP")
                        conn.commit()
                        self.logger.info("Pause columns added successfully")
                except Exception as pause_mig_err:
                    self.logger.warning(f"Pause columns migration failed: {pause_mig_err}")

                # Create worker_limits table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_limits (
                        worker_id INTEGER PRIMARY KEY,
                        hourly_limit INTEGER DEFAULT 15,
                        daily_limit INTEGER DEFAULT 150,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create admin_warnings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS admin_warnings (
                        warning_type TEXT,
                        message TEXT,
                        severity TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_resolved BOOLEAN DEFAULT 0,
                        PRIMARY KEY (warning_type, message)
                    )
                ''')

                # Meta key-value table for one-time tasks
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')

                # Create failed_group_joins table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS failed_group_joins (
                        group_id TEXT PRIMARY KEY,
                        group_name TEXT,
                        group_username TEXT,
                        fail_reason TEXT,
                        fail_count INTEGER DEFAULT 1,
                        last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        workers_tried TEXT,
                        priority TEXT DEFAULT 'medium',
                        notes TEXT
                    )
                ''')

                # Create suggestions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        suggestion_text TEXT,
                        status TEXT DEFAULT 'pending',
                        admin_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')

                # Create failed_groups table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS failed_groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id TEXT UNIQUE,
                        group_name TEXT,
                        failure_reason TEXT,
                        failure_count INTEGER DEFAULT 1,
                        last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create posting_history table for comprehensive posting tracking
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posting_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_id INTEGER,
                        slot_type TEXT DEFAULT 'user',
                        destination_id TEXT,
                        destination_name TEXT,
                        worker_id INTEGER,
                        success BOOLEAN,
                        error_message TEXT,
                        posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        message_content_hash TEXT,
                        retry_count INTEGER DEFAULT 0,
                        ban_detected BOOLEAN DEFAULT 0,
                        ban_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (slot_id) REFERENCES ad_slots(id)
                    )
                ''')

                # Create worker_bans table for tracking worker bans per destination
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_bans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER,
                        destination_id TEXT,
                        ban_type TEXT,
                        ban_reason TEXT,
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        estimated_unban_time TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Migrate existing worker_bans table to new schema
                try:
                    cursor.execute("PRAGMA table_info(worker_bans)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Add new columns if they don't exist
                    if 'destination_id' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN destination_id TEXT")
                    if 'ban_type' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN ban_type TEXT")
                    if 'ban_reason' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN ban_reason TEXT")
                    if 'estimated_unban_time' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN estimated_unban_time TIMESTAMP")
                    if 'is_active' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN is_active BOOLEAN DEFAULT 1")
                    if 'created_at' not in columns:
                        cursor.execute("ALTER TABLE worker_bans ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    
                    # Migrate existing chat_id data to destination_id if needed
                    if 'chat_id' in columns and 'destination_id' in columns:
                        cursor.execute("UPDATE worker_bans SET destination_id = CAST(chat_id AS TEXT) WHERE destination_id IS NULL")
                    
                    self.logger.info("worker_bans table migration completed")
                except Exception as wb_mig_err:
                    self.logger.warning(f"worker_bans migration failed: {wb_mig_err}")

                # Create destination_health table for tracking destination success rates
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS destination_health (
                        destination_id TEXT PRIMARY KEY,
                        destination_name TEXT,
                        total_attempts INTEGER DEFAULT 0,
                        successful_posts INTEGER DEFAULT 0,
                        failed_posts INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 100.0,
                        last_success TIMESTAMP,
                        last_failure TIMESTAMP,
                        ban_count INTEGER DEFAULT 0,
                        last_ban_time TIMESTAMP,
                        cooldown_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.commit()

                # Migrate managed_groups to allow same group in multiple categories
                try:
                    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='managed_groups'")
                    row = cursor.fetchone()
                    table_sql = row[0] if row else ''
                    if 'group_id TEXT UNIQUE' in table_sql:
                        self.logger.info("Migrating managed_groups to composite unique (group_id, category)...")
                        cursor.execute('''
                            CREATE TABLE IF NOT EXISTS managed_groups_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                group_id TEXT,
                                group_name TEXT,
                                category TEXT,
                                is_active BOOLEAN DEFAULT 1,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(group_id, category)
                            )
                        ''')
                        # Copy existing rows, dedup on (group_id, category)
                        cursor.execute('''
                            INSERT OR IGNORE INTO managed_groups_new (group_id, group_name, category, is_active, created_at)
                            SELECT group_id, group_name, category, is_active, created_at FROM managed_groups
                        ''')
                        cursor.execute('DROP TABLE managed_groups')
                        cursor.execute('ALTER TABLE managed_groups_new RENAME TO managed_groups')
                        conn.commit()
                        self.logger.info("managed_groups migration complete")
                except Exception as mg_mig_err:
                    self.logger.warning(f"managed_groups migration skipped: {mg_mig_err}")
                
                # One-time seed of predefined groups if not already done
                try:
                    cursor.execute("SELECT value FROM meta WHERE key = ?", ("seeded_predefined_groups",))
                    row = cursor.fetchone()
                    already_seeded = row and str(row[0]) == '1'
                except Exception:
                    already_seeded = False

                if not already_seeded:
                    try:
                        self._seed_predefined_groups_with_cursor(cursor)
                        cursor.execute(
                            "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
                            ("seeded_predefined_groups", '1')
                        )
                        conn.commit()
                        self.logger.info("Seeded predefined managed groups")
                    except Exception as seed_err:
                        self.logger.warning(f"Failed to seed predefined groups: {seed_err}")

                conn.close()
                
                # Run admin slots migration
                try:
                    await self.migrate_admin_slots_table()
                    self.logger.info("Admin slots migration completed")
                except Exception as migration_error:
                    self.logger.error(f"Admin slots migration failed: {migration_error}")
                
                self.logger.info("Database initialized successfully")

            except Exception as e:
                self.logger.error(f"Database initialization error: {e}")
                raise
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Validate database schema and return any issues found."""
        issues = []
        warnings = []
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=15)
            conn.execute("PRAGMA busy_timeout=15000;")
            cursor = conn.cursor()
            
            # Check required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            required_tables = {
                'users', 'ad_slots', 'payments', 'message_stats', 
                'worker_cooldowns', 'worker_activity_log', 'worker_usage', 
                'worker_health', 'worker_limits', 'admin_warnings', 
                'managed_groups', 'slot_destinations', 'meta'
            }
            
            missing_tables = required_tables - existing_tables
            if missing_tables:
                issues.append(f"Missing tables: {missing_tables}")
            
            # Check payments table columns
            cursor.execute("PRAGMA table_info(payments)")
            payments_cols = {row[1] for row in cursor.fetchall()}
            
            required_payments_cols = {
                'id', 'payment_id', 'user_id', 'amount', 'currency', 
                'crypto_type', 'status', 'payment_provider', 'provider_payment_id',
                'expected_amount_crypto', 'pay_to_address', 'network', 
                'required_confirmations', 'detected_tx_hash', 'detected_at', 
                'confirmed_at', 'created_at', 'expires_at', 'timeout_minutes', 'updated_at'
            }
            
            missing_payments_cols = required_payments_cols - payments_cols
            if missing_payments_cols:
                issues.append(f"Missing payments columns: {missing_payments_cols}")
            
            # Check ad_slots table columns
            cursor.execute("PRAGMA table_info(ad_slots)")
            ad_slots_cols = {row[1] for row in cursor.fetchall()}
            
            required_ad_slots_cols = {
                'id', 'user_id', 'slot_number', 'content', 'file_id', 
                'category', 'assigned_worker_id', 'is_active', 'interval_minutes', 
                'last_sent_at', 'created_at', 'updated_at'
            }
            
            missing_ad_slots_cols = required_ad_slots_cols - ad_slots_cols
            if missing_ad_slots_cols:
                issues.append(f"Missing ad_slots columns: {missing_ad_slots_cols}")
            
            conn.close()
            
            return {
                'status': 'healthy' if not issues else 'issues_found',
                'issues': issues,
                'warnings': warnings,
                'tables_count': len(existing_tables),
                'required_tables_count': len(required_tables)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'issues': [f"Schema validation failed: {e}"],
                'warnings': []
            }

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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                # Use UPSERT to preserve existing subscription columns
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        last_name = excluded.last_name,
                        updated_at = excluded.updated_at
                ''', (user_id, username, first_name, last_name, datetime.now()))
                conn.commit()
                conn.close()
                self.logger.info(f"User {user_id} created/updated successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error creating/updating user {user_id}: {e}")
                return False

    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's subscription information.

        Returns the stored tier and expiry, and computes is_active in Python
        to avoid SQLite string/date comparison pitfalls.
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.execute("PRAGMA busy_timeout=30000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT subscription_tier, subscription_expires 
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                conn.close()
                if not row:
                    return None

                tier = row['subscription_tier']
                expires_raw = row['subscription_expires']

                expires_dt = None
                if isinstance(expires_raw, datetime):
                    expires_dt = expires_raw
                elif isinstance(expires_raw, str) and expires_raw:
                    # Try ISO formats
                    try:
                        expires_dt = datetime.fromisoformat(expires_raw)
                    except Exception:
                        # Try common SQLite timestamp without microseconds
                        try:
                            expires_dt = datetime.strptime(expires_raw, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            expires_dt = None

                is_active = False
                if expires_dt:
                    is_active = expires_dt > datetime.now()

                return {
                    'tier': tier,
                    'expires': expires_dt or expires_raw,
                    'is_active': is_active
                }
            except Exception as e:
                self.logger.error(f"Error getting user subscription for {user_id}: {e}")
                return None

    async def update_subscription(self, user_id: int, tier: str, duration_days: int) -> bool:
        """Update user's subscription."""
        async with self._lock:
            try:
                expires = datetime.now() + timedelta(days=duration_days)
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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

    async def create_ad_slot(self, user_id: int, slot_number: int, category: str = 'general') -> Optional[int]:
        """Create a new ad slot for a user with dynamic worker assignment."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Get the number of available workers dynamically
                available_workers = await self._get_available_worker_count()
                
                # Assign worker based on slot number using round-robin across all available workers
                if available_workers > 0:
                    assigned_worker_id = ((slot_number - 1) % available_workers) + 1
                else:
                    # Fallback to worker 1 if no workers are available
                    assigned_worker_id = 1
                    self.logger.warning("No workers available, assigning to worker 1 as fallback")
                
                cursor.execute('''
                    INSERT INTO ad_slots (user_id, slot_number, category, assigned_worker_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, slot_number, category, assigned_worker_id, datetime.now()))
                slot_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                self.logger.info(f"Created ad slot {slot_id} for user {user_id} with category '{category}' assigned to worker {assigned_worker_id} (from {available_workers} available workers)")
                return slot_id
            except Exception as e:
                self.logger.error(f"Error creating ad slot: {e}")
                return None

    async def _get_available_worker_count(self) -> int:
        """Get the number of available workers from environment configuration."""
        import os
        worker_count = 0
        
        # Check for worker configurations up to worker 50 (reasonable limit)
        for i in range(1, 51):
            api_id = os.getenv(f'WORKER_{i}_API_ID')
            api_hash = os.getenv(f'WORKER_{i}_API_HASH')
            phone = os.getenv(f'WORKER_{i}_PHONE')
            
            if api_id and api_hash and phone:
                worker_count += 1
            else:
                # Stop counting when we hit the first missing worker in sequence
                # This assumes workers are numbered sequentially (1, 2, 3, etc.)
                break
        
        self.logger.debug(f"Found {worker_count} configured workers")
        return worker_count

    async def redistribute_workers_for_all_slots(self) -> bool:
        """Redistribute all ad slots across all available workers."""
        async with self._lock:
            try:
                available_workers = await self._get_available_worker_count()
                
                if available_workers == 0:
                    self.logger.warning("No workers available for redistribution")
                    return False
                
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Get all ad slots
                cursor.execute('SELECT id FROM ad_slots ORDER BY id')
                slots = cursor.fetchall()
                
                # Redistribute each slot using round-robin
                updated_count = 0
                for slot in slots:
                    slot_id = slot[0]
                    new_worker_id = ((slot_id - 1) % available_workers) + 1
                    
                    cursor.execute('''
                        UPDATE ad_slots 
                        SET assigned_worker_id = ? 
                        WHERE id = ?
                    ''', (new_worker_id, slot_id))
                    updated_count += 1
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Redistributed {updated_count} ad slots across {available_workers} workers")
                return True
                
            except Exception as e:
                self.logger.error(f"Error redistributing workers: {e}")
                return False

    async def update_slot_category(self, slot_id: int, category: str) -> bool:
        """Update slot category."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET category = ?
                    WHERE id = ?
                ''', (category, slot_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating slot category: {e}")
                return False

    async def update_slot_content(self, slot_id: int, content: str, file_id: str = None) -> bool:
        """Update slot content."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET content = ?, file_id = ?
                    WHERE id = ?
                ''', (content, file_id, slot_id))
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

    async def get_slot_destinations(self, slot_id: int, slot_type: str = 'user') -> List[Dict[str, Any]]:
        """Get all destinations for a slot (user or admin)."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if slot_type == 'admin':
                    # For admin slots, get destinations from JSON column in admin_ad_slots table
                    cursor.execute('''
                        SELECT destinations FROM admin_ad_slots WHERE id = ?
                    ''', (slot_id,))
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        try:
                            import json
                            destinations = json.loads(row[0])
                            conn.close()
                            # Convert to expected format
                            formatted_destinations = []
                            for dest in destinations:
                                formatted_destinations.append({
                                    'destination_id': dest.get('destination_id', ''),
                                    'destination_name': dest.get('destination_name', ''),
                                    'destination_type': dest.get('destination_type', 'group')
                                })
                            return formatted_destinations
                        except Exception as json_e:
                            self.logger.error(f"Error parsing admin slot destinations JSON: {json_e}")
                            conn.close()
                            return []
                    else:
                        conn.close()
                        return []
                else:
                    # For user slots, use existing logic
                    cursor.execute('''
                        SELECT * FROM slot_destinations 
                        WHERE slot_id = ? AND is_active = 1 AND COALESCE(requires_manual,0) = 0
                    ''', (slot_id,))
                    
                    destinations = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                    return destinations
                    
            except Exception as e:
                self.logger.error(f"Error getting slot destinations: {e}")
                return []

    async def flag_destination_requires_manual(self, slot_id: int, destination_id: str, error_text: str) -> bool:
        """Mark a destination as requiring manual action; record error and increment failure_count."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.execute("PRAGMA busy_timeout=30000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE slot_destinations
                    SET requires_manual = 1,
                        failure_count = COALESCE(failure_count,0) + 1,
                        last_error = ?,
                        last_error_at = ?
                    WHERE slot_id = ? AND destination_id = ?
                ''', (error_text[:240], datetime.now(), slot_id, destination_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error flagging destination requires_manual: {e}")
                return False

    async def unflag_destination(self, slot_id: int, destination_id: str) -> bool:
        """Clear requires_manual flag for a destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.execute("PRAGMA busy_timeout=30000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE slot_destinations
                    SET requires_manual = 0
                    WHERE slot_id = ? AND destination_id = ?
                ''', (slot_id, destination_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error unflagging destination: {e}")
                return False

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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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

    async def delete_user_and_data(self, user_id: int) -> bool:
        """Delete a user and all related data (ad slots, destinations, payments, stats, posts).

        Order of operations avoids FK issues:
        - Find slot ids -> delete slot_destinations, ad_posts
        - Delete ad_slots
        - Delete payments, message_stats
        - Delete user
        """
        async with self._lock:
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

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users with their subscription info."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.user_id, u.username, u.first_name, u.last_name, u.created_at,
                           u.subscription_tier, u.subscription_expires_at, 
                           CASE 
                               WHEN u.subscription_expires_at IS NULL THEN 0
                               WHEN datetime(u.subscription_expires_at) > datetime('now') THEN 1
                               ELSE 0
                           END as is_active
                    FROM users u
                    ORDER BY u.created_at DESC
                ''')
                
                users = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return users
                
            except Exception as e:
                self.logger.error(f"Error getting all users: {e}")
                return []

    async def record_payment(self, user_id: int, payment_id: str, amount: float, 
                           currency: str, status: str, expires_at: datetime, 
                           timeout_minutes: int, *, crypto_type: Optional[str] = None,
                           payment_provider: Optional[str] = None, provider_payment_id: Optional[str] = None,
                           expected_amount_crypto: Optional[float] = None,
                           pay_to_address: Optional[str] = None,
                           network: Optional[str] = None,
                           required_confirmations: Optional[int] = None,
                           attribution_method: Optional[str] = None) -> bool:
        """Record a new payment."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (
                        payment_id, user_id, amount, currency, crypto_type, status,
                        payment_provider, provider_payment_id,
                        expected_amount_crypto, pay_to_address, network, required_confirmations,
                        attribution_method, created_at, expires_at, timeout_minutes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    payment_id, user_id, amount, currency, crypto_type, status,
                    payment_provider, provider_payment_id,
                    expected_amount_crypto, pay_to_address, network, required_confirmations,
                    attribution_method or 'amount_only', datetime.now(), expires_at, timeout_minutes
                ))
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

    async def update_payment_detection(self, payment_id: str, *, detected_tx_hash: Optional[str] = None,
                                       detected_at: Optional[datetime] = None,
                                       confirmed_at: Optional[datetime] = None) -> bool:
        """Update detection metadata for a payment."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments
                    SET detected_tx_hash = COALESCE(?, detected_tx_hash),
                        detected_at = COALESCE(?, detected_at),
                        confirmed_at = COALESCE(?, confirmed_at),
                        updated_at = ?
                    WHERE payment_id = ?
                ''', (detected_tx_hash, detected_at, confirmed_at, datetime.now(), payment_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating payment detection: {e}")
                return False

    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment by ID."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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
        """Get active ad slots that are due for posting (includes both user and admin slots)."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                all_slots = []
                
                # Get active user slots that are due for posting
                cursor.execute('''
                    SELECT s.*, u.username, 'user' as slot_type
                    FROM ad_slots s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
                    )
                    ORDER BY 
                        CASE 
                            WHEN s.last_sent_at IS NULL THEN 0 
                            ELSE 1 
                        END,
                        s.last_sent_at ASC
                ''')
                
                user_slots = [dict(row) for row in cursor.fetchall()]
                all_slots.extend(user_slots)
                
                # Get active admin slots that are due for posting
                cursor.execute('''
                    SELECT s.*, 'admin' as username, 'admin' as slot_type
                    FROM admin_ad_slots s
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || COALESCE(s.interval_minutes, 60) || ' minutes')
                    )
                    ORDER BY 
                        CASE 
                            WHEN s.last_sent_at IS NULL THEN 0 
                            ELSE 1 
                        END,
                        s.last_sent_at ASC
                ''')
                
                admin_slots = [dict(row) for row in cursor.fetchall()]
                all_slots.extend(admin_slots)
                
                # Log detailed information about what slots are being selected
                for slot in all_slots:
                    slot_id = slot.get('id')
                    slot_type = slot.get('slot_type')
                    last_sent = slot.get('last_sent_at')
                    interval = slot.get('interval_minutes', 60)
                    
                    if last_sent:
                        self.logger.info(f"Slot {slot_id} ({slot_type}): Last sent at {last_sent}, interval {interval} minutes")
                    else:
                        self.logger.info(f"Slot {slot_id} ({slot_type}): No previous posts, interval {interval} minutes")
                
                conn.close()
                self.logger.info(f"Found {len(user_slots)} user slots and {len(admin_slots)} admin slots ready for posting")
                return all_slots
                
            except Exception as e:
                self.logger.error(f"Error getting active ads to send: {e}")
                return []

    async def update_slot_last_sent(self, slot_id: int, slot_type: str = 'user') -> bool:
        """Update the last_sent_at timestamp for a slot (user or admin)."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                if slot_type == 'admin':
                    cursor.execute('''
                        UPDATE admin_ad_slots 
                        SET last_sent_at = ?
                        WHERE id = ?
                    ''', (datetime.now(), slot_id))
                else:
                    cursor.execute('''
                        UPDATE ad_slots 
                        SET last_sent_at = ?
                        WHERE id = ?
                    ''', (datetime.now(), slot_id))
                    
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Admin-all virtual category: return unique chats across all categories
                if category and category.strip().lower() in ("admin_all", "__admin_all__"):
                    cursor.execute('''
                        SELECT 
                            MIN(id) as id,
                            group_id,
                            MAX(group_name) as group_name,
                            'admin_all' as category,
                            1 as is_active,
                            MIN(created_at) as created_at
                        FROM managed_groups 
                        WHERE is_active = 1 AND group_id IS NOT NULL
                        GROUP BY group_id
                        ORDER BY group_name
                    ''')
                elif category:
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
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                # Normalize category to prevent duplicates differing by case/spacing
                normalized_category = ' '.join((category or 'general').strip().split()).lower()
                cursor.execute('''
                    INSERT OR REPLACE INTO managed_groups (group_id, group_name, category)
                    VALUES (?, ?, ?)
                ''', (group_id, group_name, normalized_category))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error adding managed group: {e}")
                return False

    def _seed_predefined_groups_with_cursor(self, cursor) -> None:
        """Seed predefined categories and group usernames using an open cursor.

        Idempotent due to UNIQUE(group_id) with INSERT OR REPLACE in add_managed_group,
        but here we write directly for efficiency.
        """
        mapping = {
            'exchange services': {
                'CrystalMarketss','MafiaMarketss','qfrcemarketchat','SocialMediasGames','kwivlychat',
                'impacting','instaempiremarket','execmarket'
            },
            'telegram': {
                'CrystalMarketss','MafiaMarketss','qfrcemarketchat','SocialMediasGames','memermarket',
                'kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'discord': {
                'CrystalMarketss','MafiaMarketss','qfrcemarketchat','SocialMediasGames','memermarket',
                'kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'instagram': {
                'memermarket','CrystalMarketss','MafiaMarketss','qfrcemarketchat','SocialMediasGames',
                'kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'x/twitter': {
                'CrystalMarketss','MafiaMarketss','qfrcemarketchat','SocialMediasGames','memermarket',
                'kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'tiktok': {
                'CrystalMarketss','MafiaMarketss','MarketPlace_666','qfrcemarketchat','SocialMediasGames',
                'memermarket','kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'facebook': {
                'MarketPlace_666','qfrcemarketchat','memermarket','kwivlychat','impacting',
                'instaempiremarket','execmarket','hammermarketplace'
            },
            'youtube': {
                'CrystalMarketss','MarketPlace_666','MafiaMarketss','qfrcemarketchat','SocialMediasGames',
                'memermarket','kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'steam': {
                'CrystalMarketss','MarketPlace_666','MafiaMarketss','qfrcemarketchat','memermarket',
                'kwivlychat','impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'twitch': {
                'CrystalMarketss','impacting','MarketPlace_666','MafiaMarketss','qfrcemarketchat',
                'SocialMediasGames','memermarket','kwivlychat','instaempiremarket','execmarket','hammermarketplace'
            },
            'telegram gifts': {
                'CrystalMarketss','MarketPlace_666','MafiaMarketss','qfrcemarketchat','SocialMediasGames',
                'memermarket','kwivlychat','impacting','instaempiremarket','execmarket'
            },
            'other social media': {
                'MarketPlace_666','qfrcemarketchat','SocialMediasGames','memermarket','kwivlychat',
                'impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'gaming accounts': {
                'MarketPlace_666','qfrcemarketchat','memermarket','kwivlychat','impacting',
                'instaempiremarket','execmarket','hammermarketplace'
            },
            'gaming services': {
                'MarketPlace_666','qfrcemarketchat','SocialMediasGames','memermarket','kwivlychat',
                'impacting','instaempiremarket','execmarket'
            },
            'other services': {
                'MarketPlace_666','qfrcemarketchat','SocialMediasGames','memermarket','kwivlychat',
                'impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'other accounts': {
                'qfrcemarketchat','MarketPlace_666','SocialMediasGames','memermarket','kwivlychat',
                'impacting','instaempiremarket','execmarket','hammermarketplace'
            },
            'meme coins': {
                'MarketPlace_666','qfrcemarketchat','SocialMediasGames','kwivlychat','impacting',
                'instaempiremarket','execmarket'
            },
            'usernames': {
                'MarketPlace_666','qfrcemarketchat','memermarket','kwivlychat','impacting',
                'instaempiremarket','execmarket'
            },
            'gaming currencies': {
                'MarketPlace_666','qfrcemarketchat','kwivlychat','impacting','instaempiremarket','execmarket'
            },
            'bots and tools': {
                'MarketPlace_666','qfrcemarketchat','memermarket','impacting','instaempiremarket',
                'execmarket','hammermarketplace'
            },
            'account upgrade': {
                'MarketPlace_666','qfrcemarketchat','memermarket','kwivlychat','impacting',
                'instaempiremarket','execmarket','hammermarketplace'
            },
        }

        # Normalize and insert
        for category, users in mapping.items():
            normalized_category = ' '.join(category.strip().split()).lower()
            for uname in users:
                username = uname.strip('@')
                group_id = f"@{username}"
                # Allow same group_id in multiple categories; enforce uniqueness per category
                cursor.execute(
                    '''INSERT OR IGNORE INTO managed_groups (group_id, group_name, category, is_active, created_at)
                       VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)''',
                    (group_id, username, normalized_category)
                )

    async def remove_managed_group(self, group_name: str) -> bool:
        """Remove a managed group."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
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

    async def update_managed_group_category(self, group_id: str, category: str) -> bool:
        """Update the category for a managed group by group_id.

        Args:
            group_id: Telegram group/channel id as string (stored in managed_groups.group_id)
            category: New category name

        Returns:
            True if the update succeeded, False otherwise
        """
        async with self._lock:
            try:
                normalized_category = ' '.join(category.strip().split()).lower()
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE managed_groups
                    SET category = ?
                    WHERE group_id = ?
                ''', (normalized_category, group_id))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating managed group category: {e}")
                return False

    async def purge_managed_group_by_id(self, group_id: str) -> bool:
        """Delete a single managed group by its group_id."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('DELETE FROM managed_groups WHERE group_id = ?', (group_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error purging managed group by id: {e}")
                return False

    async def purge_managed_groups_by_category(self, category: str) -> bool:
        """Delete all managed groups within a category."""
        async with self._lock:
            try:
                normalized_category = ' '.join(category.strip().split()).lower()
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('DELETE FROM managed_groups WHERE category = ?', (normalized_category,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error purging managed groups by category: {e}")
                return False

    async def purge_all_managed_groups(self) -> bool:
        """Delete all managed groups."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('DELETE FROM managed_groups')
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error purging all managed groups: {e}")
                return False

    async def get_managed_group_categories(self) -> List[str]:
        """Return a list of distinct managed group categories."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT category FROM managed_groups ORDER BY category')
                rows = cursor.fetchall()
                conn.close()
                return [row[0] for row in rows if row[0] is not None]
            except Exception as e:
                self.logger.error(f"Error getting managed group categories: {e}")
                return []

    async def get_managed_group_category_counts(self) -> List[Dict[str, Any]]:
        """Return categories with counts of active groups."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT category, COUNT(*) as count
                    FROM managed_groups
                    WHERE is_active = 1
                    GROUP BY category
                    ORDER BY category
                ''')
                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return rows
            except Exception as e:
                self.logger.error(f"Error getting managed group category counts: {e}")
                return []

    async def activate_subscription(self, user_id: int, tier: str, duration_days: int = 30) -> bool:
        """Activate or extend user subscription.

        Avoids deadlock by not holding the internal lock while awaiting other
        methods that also acquire the lock. Reads first, then writes under lock.
        """
        try:
            # Read current subscription WITHOUT holding the lock to avoid re-entrancy deadlocks
            current_sub = await self.get_user_subscription(user_id)

            # Calculate new expiry date
            if current_sub and current_sub.get('is_active'):
                try:
                    current_expiry = datetime.fromisoformat(current_sub['expires'])
                except Exception:
                    # Fallback if stored as timestamp-like string
                    current_expiry = datetime.now()
                new_expiry = current_expiry + timedelta(days=duration_days)
            else:
                # Start new subscription
                new_expiry = datetime.now() + timedelta(days=duration_days)

            # Perform the write under the lock
            async with self._lock:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
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

    async def upgrade_user_subscription(self, user_id: int, from_tier: str, to_tier: str) -> bool:
        """Upgrade user subscription from one tier to another."""
        try:
            # Get current subscription
            current_sub = await self.get_user_subscription(user_id)
            if not current_sub:
                return False

            # Calculate remaining days
            try:
                current_expiry = datetime.fromisoformat(current_sub['expires'])
                remaining_days = (current_expiry - datetime.now()).days
                if remaining_days < 0:
                    remaining_days = 0
            except Exception:
                remaining_days = 0

            # Update subscription tier
            async with self._lock:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET subscription_tier = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (to_tier, datetime.now(), user_id))
                conn.commit()
                conn.close()

            # Update ad slots to match new tier
            await self.fix_user_ad_slots(user_id, to_tier)

            self.logger.info(f"✅ Upgraded user {user_id} from {from_tier} to {to_tier}")
            return True

        except Exception as e:
            self.logger.error(f"Error upgrading subscription: {e}")
            return False

    async def extend_user_subscription(self, user_id: int, tier: str, days: int) -> bool:
        """Extend user subscription by specified number of days."""
        try:
            # Get current subscription
            current_sub = await self.get_user_subscription(user_id)
            if not current_sub:
                return False

            # Calculate new expiry date
            try:
                current_expiry = datetime.fromisoformat(current_sub['expires'])
                if current_expiry < datetime.now():
                    # Subscription expired, start from now
                    new_expiry = datetime.now() + timedelta(days=days)
                else:
                    # Extend existing subscription
                    new_expiry = current_expiry + timedelta(days=days)
            except Exception:
                # Fallback: start from now
                new_expiry = datetime.now() + timedelta(days=days)

            # Update subscription
            async with self._lock:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET subscription_expires = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (new_expiry, datetime.now(), user_id))
                conn.commit()
                conn.close()

            self.logger.info(f"✅ Extended user {user_id} subscription by {days} days until {new_expiry}")
            return True

        except Exception as e:
            self.logger.error(f"Error extending subscription: {e}")
            return False

    async def close(self):
        """Close database connections."""
        # SQLite doesn't need explicit connection closing
        pass

    # Admin Slot Database Methods
    async def create_admin_ad_slots(self) -> bool:
        """Create the initial 20 admin ad slots."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.create_admin_ad_slots()
        except Exception as e:
            self.logger.error(f"Error creating admin ad slots: {e}")
            return False

    async def get_admin_ad_slots(self) -> List[Dict[str, Any]]:
        """Get all admin ad slots."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.get_admin_ad_slots()
        except Exception as e:
            self.logger.error(f"Error getting admin ad slots: {e}")
            return []

    async def get_admin_ad_slot(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.get_admin_ad_slot(slot_number)
        except Exception as e:
            self.logger.error(f"Error getting admin ad slot {slot_number}: {e}")
            return None
    
    async def update_admin_slot_interval(self, slot_id: int, interval_minutes: int) -> bool:
        """Update the posting interval for an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.update_admin_slot_interval(slot_id, interval_minutes)
        except Exception as e:
            self.logger.error(f"Error updating admin slot interval: {e}")
            return False
    
    async def migrate_admin_slots_table(self) -> bool:
        """Migrate admin slots table to add missing columns."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.migrate_admin_slots_table()
        except Exception as e:
            self.logger.error(f"Error migrating admin slots table: {e}")
            return False

    async def update_admin_slot_content(self, slot_id: int, content: str) -> bool:
        """Update content for an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.update_admin_slot_content(slot_id, content)
        except Exception as e:
            self.logger.error(f"Error updating admin slot content: {e}")
            return False

    async def update_admin_slot_destinations(self, slot_id: int, destinations: List[Dict[str, Any]]) -> bool:
        """Update destinations for an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.update_admin_slot_destinations(slot_id, destinations)
        except Exception as e:
            self.logger.error(f"Error updating admin slot destinations: {e}")
            return False

    async def update_admin_slot_status(self, slot_id: int, is_active: bool) -> bool:
        """Update active status for an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.update_admin_slot_status(slot_id, is_active)
        except Exception as e:
            self.logger.error(f"Error updating admin slot status: {e}")
            return False

    async def get_admin_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.get_admin_slot_destinations(slot_id)
        except Exception as e:
            self.logger.error(f"Error getting admin slot destinations: {e}")
            return []

    async def get_admin_slots_stats(self) -> Dict[str, Any]:
        """Get statistics for admin slots."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.get_admin_slots_stats()
        except Exception as e:
            self.logger.error(f"Error getting admin slots stats: {e}")
            return {}

    async def add_admin_slot_destination(self, slot_id: int, destination_data: Dict[str, Any]) -> bool:
        """Add a destination to an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.add_admin_slot_destination(slot_id, destination_data)
        except Exception as e:
            self.logger.error(f"Error adding destination to admin slot: {e}")
            return False

    async def remove_admin_slot_destination(self, slot_id: int, destination_id: str) -> bool:
        """Remove a destination from an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.remove_admin_slot_destination(slot_id, destination_id)
        except Exception as e:
            self.logger.error(f"Error removing destination from admin slot: {e}")
            return False

    async def clear_admin_slot_destinations(self, slot_id: int) -> bool:
        """Clear all destinations from an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.clear_admin_slot_destinations(slot_id)
        except Exception as e:
            self.logger.error(f"Error clearing destinations from admin slot: {e}")
            return False

    async def delete_admin_slot(self, slot_id: int) -> bool:
        """Delete an admin slot."""
        try:
            from database_admin_slots import AdminSlotDatabase
            admin_db = AdminSlotDatabase(self.db_path, self.logger)
            return await admin_db.delete_admin_slot(slot_id)
        except Exception as e:
            self.logger.error(f"Error deleting admin slot: {e}")
            return False

    async def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.execute("PRAGMA busy_timeout=60000;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

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

    async def get_or_create_ad_slots(self, user_id: int, tier: str) -> List[Dict[str, Any]]:
        """Get existing ad slots for a user based on tier, creating missing ones if needed.

        Slot allocation by tier:
        - basic: 1 slot
        - pro: 3 slots
        - enterprise: 5 slots
        """
        tier_normalized = (tier or "basic").strip().lower()
        required_slots = 1 if tier_normalized == "basic" else (3 if tier_normalized == "pro" else 5)
        
        self.logger.info(f"get_or_create_ad_slots: user_id={user_id}, tier={tier}, required_slots={required_slots}")
        
        # First, clean up excess slots if user has more than their tier allows
        await self._cleanup_excess_ad_slots(user_id, required_slots)

        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Check if ad_slots table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ad_slots'")
                table_exists = cursor.fetchone() is not None
                self.logger.info(f"get_or_create_ad_slots: ad_slots table exists: {table_exists}")
                
                if not table_exists:
                    self.logger.error("ad_slots table does not exist!")
                    return []
                
                # Count existing slots
                cursor.execute("SELECT COUNT(1) FROM ad_slots WHERE user_id = ?", (user_id,))
                existing_count = cursor.fetchone()[0]
                self.logger.info(f"get_or_create_ad_slots: existing_count={existing_count}")

                # Create missing slots
                if existing_count < required_slots:
                    self.logger.info(f"get_or_create_ad_slots: creating {required_slots - existing_count} new slots")
                    for slot_number in range(existing_count + 1, required_slots + 1):
                        cursor.execute(
                            '''INSERT INTO ad_slots (user_id, slot_number, category, assigned_worker_id, is_active, interval_minutes, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (user_id, slot_number, 'general', 1, 0, 60, datetime.now())
                        )
                    conn.commit()
                    self.logger.info(f"get_or_create_ad_slots: created slots successfully")

                # Fetch and return slots mapped to expected keys
                cursor.execute(
                    "SELECT id, slot_number, content, is_active, interval_minutes FROM ad_slots WHERE user_id = ? ORDER BY slot_number",
                    (user_id,)
                )
                rows = cursor.fetchall()
                conn.close()

                slots: List[Dict[str, Any]] = []
                for row in rows:
                    slot_dict = dict(row)
                    # Map DB 'content' to API 'ad_content' expected by user_commands
                    slot_dict['ad_content'] = slot_dict.pop('content', None)
                    slots.append(slot_dict)
                
                self.logger.info(f"get_or_create_ad_slots: returning {len(slots)} slots: {slots}")
                return slots
            except Exception as e:
                self.logger.error(f"Error in get_or_create_ad_slots: {e}")
                return []

    async def _cleanup_excess_ad_slots(self, user_id: int, max_slots: int) -> None:
        """Remove excess ad slots if user has more than their tier allows."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA busy_timeout=30000;")
            cursor = conn.cursor()
            
            # Count current slots
            cursor.execute("SELECT COUNT(1) FROM ad_slots WHERE user_id = ?", (user_id,))
            current_count = cursor.fetchone()[0]
            
            if current_count > max_slots:
                self.logger.info(f"Cleaning up excess ad slots: user {user_id} has {current_count} slots, tier allows {max_slots}")
                
                # Get slots ordered by slot_number (keep lowest numbered slots)
                cursor.execute(
                    "SELECT id FROM ad_slots WHERE user_id = ? ORDER BY slot_number",
                    (user_id,)
                )
                slot_ids = [row[0] for row in cursor.fetchall()]
                
                # Remove excess slots (keep first max_slots)
                excess_slot_ids = slot_ids[max_slots:]
                if excess_slot_ids:
                    placeholders = ','.join(['?' for _ in excess_slot_ids])
                    cursor.execute(
                        f"DELETE FROM ad_slots WHERE id IN ({placeholders})",
                        excess_slot_ids
                    )
                    conn.commit()
                    self.logger.info(f"Removed {len(excess_slot_ids)} excess ad slots for user {user_id}")
            
            conn.close()
        except Exception as e:
            self.logger.error(f"Error cleaning up excess ad slots: {e}")

    async def get_ad_slot_by_id(self, slot_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single ad slot by its ID."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.execute("PRAGMA busy_timeout=30000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, user_id, slot_number, content, file_id, category, assigned_worker_id, is_active, interval_minutes, last_sent_at FROM ad_slots WHERE id = ?",
                    (slot_id,)
                )
                row = cursor.fetchone()
                conn.close()
                if not row:
                    return None
                slot = dict(row)
                slot['ad_content'] = slot.pop('content', None)
                return slot
            except Exception as e:
                self.logger.error(f"Error in get_ad_slot_by_id({slot_id}): {e}")
                return None

    async def update_ad_slot_content(self, slot_id: int, content: str, file_id: Optional[str] = None) -> bool:
        """Update the content and optional file_id for an ad slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                cursor = conn.cursor()
                # Ensure updated_at column exists (lazy migration)
                try:
                    cursor.execute("PRAGMA table_info(ad_slots)")
                    cols = {row[1] for row in cursor.fetchall()}
                    if 'updated_at' not in cols:
                        try:
                            cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TIMESTAMP")
                        except Exception:
                            pass
                except Exception:
                    pass
                # Try update with updated_at; on failure, retry without
                try:
                    cursor.execute(
                        "UPDATE ad_slots SET content = ?, file_id = ?, updated_at = ? WHERE id = ?",
                        (content, file_id, datetime.now(), slot_id)
                    )
                except Exception:
                    cursor.execute(
                        "UPDATE ad_slots SET content = ?, file_id = ? WHERE id = ?",
                        (content, file_id, slot_id)
                    )
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating ad slot content: {e}")
                return False

    async def update_ad_slot_schedule(self, slot_id: int, interval_minutes: int) -> bool:
        """Update the schedule interval for an ad slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                cursor = conn.cursor()
                # Ensure updated_at exists; then attempt update
                try:
                    cursor.execute("PRAGMA table_info(ad_slots)")
                    cols = {row[1] for row in cursor.fetchall()}
                    if 'updated_at' not in cols:
                        try:
                            cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TIMESTAMP")
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    cursor.execute(
                        "UPDATE ad_slots SET interval_minutes = ?, updated_at = ? WHERE id = ?",
                        (interval_minutes, datetime.now(), slot_id)
                    )
                except Exception:
                    cursor.execute(
                        "UPDATE ad_slots SET interval_minutes = ? WHERE id = ?",
                        (interval_minutes, slot_id)
                    )
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating ad slot schedule: {e}")
                return False

    async def update_ad_slot_status(self, slot_id: int, is_active: bool) -> bool:
        """Pause or resume an ad slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                cursor = conn.cursor()
                # Ensure updated_at exists; then attempt update
                try:
                    cursor.execute("PRAGMA table_info(ad_slots)")
                    cols = {row[1] for row in cursor.fetchall()}
                    if 'updated_at' not in cols:
                        try:
                            cursor.execute("ALTER TABLE ad_slots ADD COLUMN updated_at TIMESTAMP")
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    cursor.execute(
                        "UPDATE ad_slots SET is_active = ?, updated_at = ? WHERE id = ?",
                        (1 if is_active else 0, datetime.now(), slot_id)
                    )
                except Exception:
                    cursor.execute(
                        "UPDATE ad_slots SET is_active = ? WHERE id = ?",
                        (1 if is_active else 0, slot_id)
                    )
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating ad slot status: {e}")
                return False

    async def get_destinations_for_slot(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get active destinations for a given ad slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30)
                conn.execute("PRAGMA busy_timeout=30000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, destination_type, destination_id, destination_name, alias, is_active FROM slot_destinations WHERE slot_id = ? AND is_active = 1",
                    (slot_id,)
                )
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
            except Exception as e:
                self.logger.error(f"Error getting destinations for slot {slot_id}: {e}")
                return []

    async def update_destinations_for_slot(self, slot_id: int, destinations: List[Dict[str, Any]]) -> bool:
        """Replace destinations for a slot with the provided list.

        destinations: list of dicts with keys: destination_type, destination_id, destination_name (optional), alias (optional)
        """
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                cursor = conn.cursor()
                
                # Get user_id for this slot to implement user-specific restart
                cursor.execute("SELECT user_id FROM ad_slots WHERE id = ?", (slot_id,))
                slot_user = cursor.fetchone()
                if not slot_user:
                    conn.close()
                    return False
                
                user_id = slot_user[0]
                
                # Pause posting for this user temporarily
                cursor.execute("""
                    UPDATE ad_slots 
                    SET is_paused = 1, pause_reason = 'destination_change', pause_time = ?
                    WHERE user_id = ?
                """, (datetime.now(), user_id))
                
                # Remove existing destinations for the slot
                cursor.execute("DELETE FROM slot_destinations WHERE slot_id = ?", (slot_id,))
                
                # Insert new ones
                for dest in destinations:
                    cursor.execute(
                        '''INSERT INTO slot_destinations (slot_id, destination_type, destination_id, destination_name, alias, is_active, created_at)
                           VALUES (?, ?, ?, ?, ?, 1, ?)''',
                        (
                            slot_id,
                            dest.get('destination_type'),
                            dest.get('destination_id'),
                            dest.get('destination_name'),
                            dest.get('alias'),
                            datetime.now(),
                        )
                    )
                
                # Resume posting for this user after a brief delay
                cursor.execute("""
                    UPDATE ad_slots 
                    SET is_paused = 0, pause_reason = NULL, pause_time = NULL
                    WHERE user_id = ?
                """, (user_id,))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Error updating destinations for slot {slot_id}: {e}")
                return False

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
        """Get active ad slots with their destinations."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get active ad slots with their destinations
                cursor.execute('''
                    SELECT 
                        ads.id,
                        ads.user_id,
                        ads.slot_number,
                        ads.content,
                        ads.file_id,
                        ads.interval_minutes,
                        ads.last_sent_at,
                        ads.created_at,
                        GROUP_CONCAT(sd.destination_id) as destinations,
                        GROUP_CONCAT(sd.destination_name) as destination_names
                    FROM ad_slots ads
                    LEFT JOIN slot_destinations sd ON ads.id = sd.slot_id AND sd.is_active = 1
                    WHERE ads.is_active = 1
                    GROUP BY ads.id
                ''')
                
                slots = []
                for row in cursor.fetchall():
                    slot_data = dict(row)
                    # Parse destinations
                    if slot_data['destinations']:
                        slot_data['destinations'] = slot_data['destinations'].split(',')
                        slot_data['destination_names'] = slot_data['destination_names'].split(',')
                    else:
                        slot_data['destinations'] = []
                        slot_data['destination_names'] = []
                    
                    slots.append(slot_data)
                
                conn.close()
                self.logger.info(f"Found {len(slots)} active ad slots")
                return slots
                
            except Exception as e:
                self.logger.error(f"Error getting active ad slots: {e}")
                return []

    async def get_ad_destinations(self, *args, **kwargs):
        """get_ad_destinations - merged from PostgreSQL database."""
        # TODO: Implement this method for SQLite
        self.logger.warning(f"Method get_ad_destinations not yet implemented for SQLite")
        return None

    # Worker-related methods
    async def get_all_workers(self) -> List[Dict[str, Any]]:
        """Get all workers from the database."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT worker_id, created_at, is_active
                    FROM worker_cooldowns
                    WHERE is_active = 1
                    ORDER BY worker_id
                ''')
                
                workers = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                self.logger.info(f"Found {len(workers)} workers")
                return workers
                
            except Exception as e:
                self.logger.error(f"Error getting all workers: {e}")
                return []

    async def get_available_workers(self) -> List[Dict[str, Any]]:
        """Get workers that are available (not at their limits)."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get workers with their usage and health data
                cursor.execute('''
                    SELECT 
                        w.worker_id,
                        w.created_at,
                        w.is_active,
                        COALESCE(wu.hourly_posts, 0) as hourly_posts,
                        COALESCE(wu.daily_posts, 0) as daily_posts,
                        COALESCE(wl.hourly_limit, 15) as hourly_limit,
                        COALESCE(wl.daily_limit, 150) as daily_limit,
                        COALESCE(wh.success_rate, 100.0) as success_rate,
                        COALESCE(wh.ban_count, 0) as ban_count,
                        COALESCE(wh.error_count, 0) as error_count
                    FROM worker_cooldowns w
                    LEFT JOIN worker_usage wu ON w.worker_id = wu.worker_id 
                        AND wu.hour = strftime('%Y-%m-%d %H:00:00', 'now')
                    LEFT JOIN worker_health wh ON w.worker_id = wh.worker_id
                    LEFT JOIN worker_limits wl ON w.worker_id = wl.worker_id
                    WHERE w.is_active = 1
                    AND (wu.hourly_posts IS NULL OR wu.hourly_posts < wl.hourly_limit)
                    AND (wu.daily_posts IS NULL OR wu.daily_posts < wl.daily_limit)
                    ORDER BY wh.success_rate DESC, wu.hourly_posts ASC, wu.daily_posts ASC
                ''')
                
                workers = []
                for row in cursor.fetchall():
                    worker_data = dict(row)
                    
                    # Calculate usage percentages
                    hourly_limit = worker_data.get('hourly_limit', 15)
                    daily_limit = worker_data.get('daily_limit', 150)
                    
                    hourly_posts = worker_data.get('hourly_posts', 0)
                    daily_posts = worker_data.get('daily_posts', 0)
                    
                    worker_data['hourly_usage_percent'] = (hourly_posts / hourly_limit * 100) if hourly_limit > 0 else 0
                    worker_data['daily_usage_percent'] = (daily_posts / daily_limit * 100) if daily_limit > 0 else 0
                    
                    # Calculate safety score
                    success_rate = worker_data.get('success_rate', 100.0)
                    ban_count = worker_data.get('ban_count', 0)
                    error_count = worker_data.get('error_count', 0)
                    
                    safety_score = success_rate - (ban_count * 10) - (error_count * 5)
                    worker_data['safety_score'] = max(0, min(100, safety_score))
                    
                    # Check if available
                    worker_data['is_available'] = (
                        hourly_posts < hourly_limit and 
                        daily_posts < daily_limit
                    )
                    
                    workers.append(worker_data)
                
                conn.close()
                
                self.logger.info(f"Found {len(workers)} available workers")
                return workers
                
            except Exception as e:
                self.logger.error(f"Error getting available workers: {e}")
                return []

    async def get_worker_usage(self, worker_id: int) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a specific worker."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get current hour and day usage
                cursor.execute('''
                    SELECT 
                        COALESCE(wu.hourly_posts, 0) as hourly_posts,
                        COALESCE(wu.daily_posts, 0) as daily_posts,
                        COALESCE(wl.hourly_limit, 15) as hourly_limit,
                        COALESCE(wl.daily_limit, 150) as daily_limit,
                        COALESCE(wh.success_rate, 100.0) as success_rate,
                        COALESCE(wh.error_count, 0) as error_count
                    FROM worker_cooldowns w
                    LEFT JOIN worker_usage wu ON w.worker_id = wu.worker_id 
                        AND wu.hour = strftime('%Y-%m-%d %H:00:00', 'now')
                    LEFT JOIN worker_health wh ON w.worker_id = wh.worker_id
                    LEFT JOIN worker_limits wl ON w.worker_id = wl.worker_id
                    WHERE w.worker_id = ?
                ''', (worker_id,))
                
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return None
                
                usage_data = dict(row)
                
                # Calculate percentages and safety score
                hourly_limit = usage_data.get('hourly_limit', 15)
                daily_limit = usage_data.get('daily_limit', 150)
                
                hourly_posts = usage_data.get('hourly_posts', 0)
                daily_posts = usage_data.get('daily_posts', 0)
                
                usage_data['hourly_usage_percent'] = (hourly_posts / hourly_limit * 100) if hourly_limit > 0 else 0
                usage_data['daily_usage_percent'] = (daily_posts / daily_limit * 100) if daily_limit > 0 else 0
                
                success_rate = usage_data.get('success_rate', 100.0)
                error_count = usage_data.get('error_count', 0)
                
                safety_score = success_rate - (error_count * 5)
                usage_data['safety_score'] = max(0, min(100, safety_score))
                
                usage_data['is_available'] = (
                    hourly_posts < hourly_limit and 
                    daily_posts < daily_limit
                )
                
                conn.close()
                return usage_data
                
            except Exception as e:
                self.logger.error(f"Error getting worker usage for {worker_id}: {e}")
                return None

    async def record_worker_post(self, worker_id: int, success: bool, error: str = None) -> bool:
        """Record a worker's post attempt and update usage/health statistics."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                current_hour = datetime.now().strftime('%Y-%m-%d %H:00:00')
                current_day = datetime.now().strftime('%Y-%m-%d')
                
                # Update or create hourly usage
                try:
                    cursor.execute('''
                        INSERT INTO worker_usage (worker_id, hour, hourly_posts, day, daily_posts)
                        VALUES (?, ?, 1, ?, 1)
                        ON CONFLICT(worker_id, hour) DO UPDATE SET
                        hourly_posts = hourly_posts + 1,
                        daily_posts = daily_posts + 1
                    ''', (worker_id, current_hour, current_day))
                except Exception as usage_err:
                    # Fallback: try to recreate the table with correct schema
                    self.logger.warning(f"Worker usage table schema issue, recreating: {usage_err}")
                    cursor.execute("DROP TABLE IF EXISTS worker_usage")
                    cursor.execute('''
                        CREATE TABLE worker_usage (
                            worker_id INTEGER,
                            hour TEXT,
                            hourly_posts INTEGER DEFAULT 0,
                            daily_posts INTEGER DEFAULT 0,
                            day TEXT,
                            PRIMARY KEY (worker_id, hour)
                        )
                    ''')
                    cursor.execute('''
                        INSERT INTO worker_usage (worker_id, hour, hourly_posts, day, daily_posts)
                        VALUES (?, ?, 1, ?, 1)
                    ''', (worker_id, current_hour, current_day))
                
                # Update health statistics
                if success:
                    cursor.execute('''
                        INSERT INTO worker_health (worker_id, successful_posts, total_posts, success_rate)
                        VALUES (?, 1, 1, 100.0)
                        ON CONFLICT(worker_id) DO UPDATE SET
                        successful_posts = successful_posts + 1,
                        total_posts = total_posts + 1,
                        success_rate = (successful_posts + 1.0) / (total_posts + 1.0) * 100.0
                    ''', (worker_id,))
                else:
                    cursor.execute('''
                        INSERT INTO worker_health (worker_id, successful_posts, total_posts, success_rate, error_count)
                        VALUES (?, 0, 1, 0.0, 1)
                        ON CONFLICT(worker_id) DO UPDATE SET
                        total_posts = total_posts + 1,
                        error_count = error_count + 1,
                        success_rate = (successful_posts * 1.0) / (total_posts + 1.0) * 100.0
                    ''', (worker_id,))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Recorded worker {worker_id} post: success={success}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error recording worker post for {worker_id}: {e}")
                return False

    async def create_admin_warning(self, warning_type: str, message: str, severity: str = "medium") -> bool:
        """Create an admin warning."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO admin_warnings (warning_type, message, severity, created_at, is_resolved)
                    VALUES (?, ?, ?, ?, 0)
                ''', (warning_type, message, severity, datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Created admin warning: {warning_type} - {message}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error creating admin warning: {e}")
                return False

    async def get_unresolved_warnings(self) -> List[Dict[str, Any]]:
        """Get all unresolved admin warnings."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT warning_type, message, severity, created_at
                    FROM admin_warnings
                    WHERE is_resolved = 0
                    ORDER BY created_at DESC
                ''')
                
                warnings = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                return warnings
                
            except Exception as e:
                self.logger.error(f"Error getting unresolved warnings: {e}")
                return []

    async def initialize_worker_limits(self, worker_id: int) -> bool:
        """Initialize worker limits for a new worker."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO worker_limits (worker_id, hourly_limit, daily_limit, created_at)
                    VALUES (?, 15, 150, ?)
                ''', (worker_id, datetime.now()))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Initialized limits for worker {worker_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error initializing worker limits for {worker_id}: {e}")
                return False

    async def increase_worker_limits(self, worker_id: int) -> bool:
        """Increase worker limits by 10% (rounded up) weekly."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Get current limits
                cursor.execute('''
                    SELECT hourly_limit, daily_limit FROM worker_limits WHERE worker_id = ?
                ''', (worker_id,))
                
                row = cursor.fetchone()
                if not row:
                    # Initialize if not exists
                    await self.initialize_worker_limits(worker_id)
                    cursor.execute('''
                        SELECT hourly_limit, daily_limit FROM worker_limits WHERE worker_id = ?
                    ''', (worker_id,))
                    row = cursor.fetchone()
                
                current_hourly, current_daily = row
                
                # Calculate new limits (10% increase, rounded up, max 100/1500)
                new_hourly = min(100, math.ceil(current_hourly * 1.1))
                new_daily = min(1500, math.ceil(current_daily * 1.1))
                
                cursor.execute('''
                    UPDATE worker_limits 
                    SET hourly_limit = ?, daily_limit = ?, updated_at = ?
                    WHERE worker_id = ?
                ''', (new_hourly, new_daily, datetime.now(), worker_id))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Increased limits for worker {worker_id}: {current_hourly}/{current_daily} -> {new_hourly}/{new_daily}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error increasing worker limits for {worker_id}: {e}")
                return False

    async def fix_user_ad_slots(self, user_id: int, correct_tier: str) -> bool:
        """Fix user's ad slots to match their correct subscription tier."""
        async with self._lock:
            try:
                # First, update the user's subscription tier
                await self.update_subscription(user_id, correct_tier, 30)  # 30 days
                
                # Get the correct number of slots for the tier
                tier_normalized = correct_tier.strip().lower()
                correct_slot_count = 1 if tier_normalized == "basic" else (3 if tier_normalized == "pro" else 5)
                
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Count current slots
                cursor.execute("SELECT COUNT(1) FROM ad_slots WHERE user_id = ?", (user_id,))
                current_count = cursor.fetchone()[0]
                
                if current_count > correct_slot_count:
                    # Delete excess slots (keep the first N slots)
                    cursor.execute('''
                        DELETE FROM ad_slots 
                        WHERE user_id = ? AND slot_number > ?
                    ''', (user_id, correct_slot_count))
                    
                    # Also delete destinations for deleted slots
                    cursor.execute('''
                        DELETE FROM slot_destinations 
                        WHERE slot_id IN (
                            SELECT id FROM ad_slots WHERE user_id = ? AND slot_number > ?
                        )
                    ''', (user_id, correct_slot_count))
                    
                    self.logger.info(f"Fixed user {user_id} ad slots: removed {current_count - correct_slot_count} excess slots")
                elif current_count < correct_slot_count:
                    # Add missing slots
                    for slot_number in range(current_count + 1, correct_slot_count + 1):
                        cursor.execute(
                            '''INSERT INTO ad_slots (user_id, slot_number, category, assigned_worker_id, is_active, interval_minutes, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (user_id, slot_number, 'general', 1, 0, 60, datetime.now())
                        )
                    self.logger.info(f"Fixed user {user_id} ad slots: added {correct_slot_count - current_count} missing slots")
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Successfully fixed ad slots for user {user_id} to {correct_tier} tier ({correct_slot_count} slots)")
                return True
                
            except Exception as e:
                self.logger.error(f"Error fixing ad slots for user {user_id}: {e}")
                return False

    async def record_failed_group_join(self, group_id: str, group_name: str, group_username: str, 
                                      fail_reason: str, worker_id: int, priority: str = 'medium') -> bool:
        """Record a failed group join attempt."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Check if group already exists in failed joins
                cursor.execute('''
                    SELECT fail_count, workers_tried FROM failed_group_joins 
                    WHERE group_id = ?
                ''', (group_id,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    fail_count = existing[0] + 1
                    workers_tried = existing[1] or ""
                    if str(worker_id) not in workers_tried:
                        workers_tried += f",{worker_id}" if workers_tried else str(worker_id)
                    
                    cursor.execute('''
                        UPDATE failed_group_joins 
                        SET fail_count = ?, last_attempt = CURRENT_TIMESTAMP, 
                            workers_tried = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE group_id = ?
                    ''', (fail_count, workers_tried, group_id))
                else:
                    # Create new record
                    cursor.execute('''
                        INSERT INTO failed_group_joins 
                        (group_id, group_name, group_username, fail_reason, workers_tried, priority)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (group_id, group_name, group_username, fail_reason, str(worker_id), priority))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error recording failed group join: {e}")
                return False

    async def get_failed_group_joins(self, priority: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failed group joins, optionally filtered by priority."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if priority:
                    cursor.execute('''
                        SELECT * FROM failed_group_joins 
                        WHERE priority = ?
                        ORDER BY fail_count DESC, last_attempt DESC
                        LIMIT ?
                    ''', (priority, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM failed_group_joins 
                        ORDER BY priority DESC, fail_count DESC, last_attempt DESC
                        LIMIT ?
                    ''', (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append(dict(row))
                
                conn.close()
                return results
                
            except Exception as e:
                self.logger.error(f"Error getting failed group joins: {e}")
                return []

    async def update_failed_group_priority(self, group_id: str, priority: str) -> bool:
        """Update priority of a failed group join."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE failed_group_joins 
                    SET priority = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE group_id = ?
                ''', (priority, group_id))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating failed group priority: {e}")
                return False

    async def remove_failed_group_join(self, group_id: str) -> bool:
        """Remove a group from failed joins (when manually resolved)."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM failed_group_joins WHERE group_id = ?', (group_id,))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error removing failed group join: {e}")
                return False

    async def get_failed_group_stats(self) -> Dict[str, Any]:
        """Get statistics about failed group joins."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Get total counts by reason
                cursor.execute('''
                    SELECT fail_reason, COUNT(*) as count, SUM(fail_count) as total_attempts
                    FROM failed_group_joins 
                    GROUP BY fail_reason
                ''')
                
                reason_stats = {}
                for row in cursor.fetchall():
                    reason_stats[row[0]] = {
                        'count': row[1],
                        'total_attempts': row[2]
                    }
                
                # Get counts by priority
                cursor.execute('''
                    SELECT priority, COUNT(*) as count
                    FROM failed_group_joins 
                    GROUP BY priority
                ''')
                
                priority_stats = {}
                for row in cursor.fetchall():
                    priority_stats[row[0]] = row[1]
                
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM failed_group_joins')
                total_count = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_failed_groups': total_count,
                    'by_reason': reason_stats,
                    'by_priority': priority_stats
                }
                
            except Exception as e:
                self.logger.error(f"Error getting failed group stats: {e}")
                return {}

    async def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all user subscriptions."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, subscription_tier, subscription_expires, created_at, updated_at
                    FROM users 
                    WHERE subscription_tier IS NOT NULL
                ''')
                
                subscriptions = []
                for row in cursor.fetchall():
                    subscriptions.append({
                        'user_id': row[0],
                        'tier': row[1],
                        'expires': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
                
                conn.close()
                return subscriptions
                
            except Exception as e:
                self.logger.error(f"Error getting all subscriptions: {e}")
                return []

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and all associated data."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                # Delete user's ad slots
                cursor.execute('DELETE FROM ad_slots WHERE user_id = ?', (user_id,))
                
                # Delete user's slot destinations
                cursor.execute('''
                    DELETE FROM slot_destinations 
                    WHERE slot_id IN (SELECT id FROM ad_slots WHERE user_id = ?)
                ''', (user_id,))
                
                # Delete user's payments
                cursor.execute('DELETE FROM payments WHERE user_id = ?', (user_id,))
                
                # Delete user
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                
                conn.commit()
                conn.close()
                return True
                
            except Exception as e:
                self.logger.error(f"Error deleting user {user_id}: {e}")
                return False

    async def get_all_ad_slots(self) -> List[Dict[str, Any]]:
        """Get all ad slots."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, user_id, slot_number, content, is_active, interval_minutes, created_at, updated_at
                    FROM ad_slots
                ''')
                
                ad_slots = []
                for row in cursor.fetchall():
                    ad_slots.append({
                        'id': row[0],
                        'user_id': row[1],
                        'slot_number': row[2],
                        'content': row[3],
                        'is_active': bool(row[4]),
                        'interval_minutes': row[5],
                        'created_at': row[6],
                        'updated_at': row[7]
                    })
                
                conn.close()
                return ad_slots
                
            except Exception as e:
                self.logger.error(f"Error getting all ad slots: {e}")
                return []

    async def get_all_payments(self) -> List[Dict[str, Any]]:
        """Get all payments."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT payment_id, user_id, amount, currency, status, created_at, expires_at
                    FROM payments
                ''')
                
                payments = []
                for row in cursor.fetchall():
                    payments.append({
                        'payment_id': row[0],
                        'user_id': row[1],
                        'amount': row[2],
                        'currency': row[3],
                        'status': row[4],
                        'created_at': row[5],
                        'expires_at': row[6]
                    })
                
                conn.close()
                return payments
                
            except Exception as e:
                self.logger.error(f"Error getting all payments: {e}")
                return []

    async def get_ad_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific ad slot."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=60)
                conn.execute("PRAGMA busy_timeout=60000;")
                conn.execute("PRAGMA journal_mode=WAL;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT destination_id, destination_name, destination_type, created_at
                    FROM slot_destinations 
                    WHERE slot_id = ?
                ''', (slot_id,))
                
                destinations = []
                for row in cursor.fetchall():
                    destinations.append({
                        'destination_id': row[0],
                        'destination_name': row[1],
                        'destination_type': row[2],
                        'created_at': row[3]
                    })
                
                conn.close()
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting ad slot destinations: {e}")
                return []

    async def get_connection(self):
        """Get a database connection for testing."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=60)
            conn.execute("PRAGMA busy_timeout=60000;")
            conn.execute("PRAGMA journal_mode=WAL;")
            return conn
        except Exception as e:
            self.logger.error(f"Error getting database connection: {e}")
            return None

    def close(self):
        """Close the database manager."""
        pass

    # ============================================================================
    # POSTING HISTORY METHODS
    # ============================================================================

    async def record_posting_attempt(self, slot_id: int, slot_type: str, destination_id: str, 
                                   destination_name: str, worker_id: int, success: bool, 
                                   error_message: str = None, message_content_hash: str = None,
                                   ban_detected: bool = False, ban_type: str = None) -> bool:
        """Record a posting attempt in the posting history."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO posting_history (
                        slot_id, slot_type, destination_id, destination_name, worker_id,
                        success, error_message, posted_at, message_content_hash,
                        ban_detected, ban_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                ''', (slot_id, slot_type, destination_id, destination_name, worker_id,
                     success, error_message, message_content_hash, ban_detected, ban_type))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Recorded posting attempt: slot={slot_id}, dest={destination_id}, success={success}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error recording posting attempt: {e}")
                return False

    async def get_posting_history(self, slot_id: int = None, destination_id: str = None, 
                                worker_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posting history with optional filters."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM posting_history 
                    WHERE 1=1
                '''
                params = []
                
                if slot_id:
                    query += ' AND slot_id = ?'
                    params.append(slot_id)
                
                if destination_id:
                    query += ' AND destination_id = ?'
                    params.append(destination_id)
                
                if worker_id:
                    query += ' AND worker_id = ?'
                    params.append(worker_id)
                
                query += ' ORDER BY posted_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                history = [dict(row) for row in cursor.fetchall()]
                
                conn.close()
                return history
                
            except Exception as e:
                self.logger.error(f"Error getting posting history: {e}")
                return []

    async def get_recent_posting_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent posting activity statistics."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Get total posts in time period
                cursor.execute('''
                    SELECT COUNT(*) FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours')
                '''.format(hours))
                total_posts = cursor.fetchone()[0]
                
                # Get successful posts
                cursor.execute('''
                    SELECT COUNT(*) FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours') AND success = 1
                '''.format(hours))
                successful_posts = cursor.fetchone()[0]
                
                # Get failed posts
                cursor.execute('''
                    SELECT COUNT(*) FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours') AND success = 0
                '''.format(hours))
                failed_posts = cursor.fetchone()[0]
                
                # Get ban detections
                cursor.execute('''
                    SELECT COUNT(*) FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours') AND ban_detected = 1
                '''.format(hours))
                ban_detections = cursor.fetchone()[0]
                
                # Get top destinations
                cursor.execute('''
                    SELECT destination_id, COUNT(*) as post_count 
                    FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours')
                    GROUP BY destination_id 
                    ORDER BY post_count DESC 
                    LIMIT 10
                '''.format(hours))
                top_destinations = [{'destination_id': row[0], 'post_count': row[1]} for row in cursor.fetchall()]
                
                # Get top workers
                cursor.execute('''
                    SELECT worker_id, COUNT(*) as post_count 
                    FROM posting_history 
                    WHERE posted_at >= datetime('now', '-{} hours')
                    GROUP BY worker_id 
                    ORDER BY post_count DESC 
                    LIMIT 10
                '''.format(hours))
                top_workers = [{'worker_id': row[0], 'post_count': row[1]} for row in cursor.fetchall()]
                
                conn.close()
                
                success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0
                
                return {
                    'total_posts': total_posts,
                    'successful_posts': successful_posts,
                    'failed_posts': failed_posts,
                    'ban_detections': ban_detections,
                    'success_rate': round(success_rate, 2),
                    'top_destinations': top_destinations,
                    'top_workers': top_workers,
                    'time_period_hours': hours
                }
                
            except Exception as e:
                self.logger.error(f"Error getting recent posting activity: {e}")
                return {
                    'total_posts': 0,
                    'successful_posts': 0,
                    'failed_posts': 0,
                    'ban_detections': 0,
                    'success_rate': 0,
                    'top_destinations': [],
                    'top_workers': [],
                    'time_period_hours': hours
                }

    # ============================================================================
    # BAN TRACKING METHODS
    # ============================================================================

    async def record_worker_ban(self, worker_id: int, destination_id: str, ban_type: str, 
                               ban_reason: str, estimated_unban_time: str = None) -> bool:
        """Record a worker ban for a specific destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO worker_bans (
                        worker_id, destination_id, ban_type, ban_reason, 
                        banned_at, estimated_unban_time, is_active
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
                ''', (worker_id, destination_id, ban_type, ban_reason, estimated_unban_time))
                
                conn.commit()
                conn.close()
                
                self.logger.warning(f"Recorded worker ban: worker={worker_id}, dest={destination_id}, type={ban_type}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error recording worker ban: {e}")
                return False

    async def get_worker_bans(self, worker_id: int = None, destination_id: str = None, 
                            active_only: bool = True) -> List[Dict[str, Any]]:
        """Get worker bans with optional filters."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM worker_bans 
                    WHERE 1=1
                '''
                params = []
                
                if worker_id:
                    query += ' AND worker_id = ?'
                    params.append(worker_id)
                
                if destination_id:
                    query += ' AND destination_id = ?'
                    params.append(destination_id)
                
                if active_only:
                    query += ' AND is_active = 1'
                
                query += ' ORDER BY banned_at DESC'
                
                cursor.execute(query, params)
                bans = [dict(row) for row in cursor.fetchall()]
                
                conn.close()
                return bans
                
            except Exception as e:
                self.logger.error(f"Error getting worker bans: {e}")
                return []

    async def is_worker_banned(self, worker_id: int, destination_id: str) -> bool:
        """Check if a worker is banned from a specific destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM worker_bans 
                    WHERE worker_id = ? AND destination_id = ? AND is_active = 1
                ''', (worker_id, destination_id))
                
                ban_count = cursor.fetchone()[0]
                conn.close()
                
                return ban_count > 0
                
            except Exception as e:
                self.logger.error(f"Error checking worker ban status: {e}")
                return False

    async def clear_worker_ban(self, worker_id: int, destination_id: str) -> bool:
        """Clear a worker ban for a specific destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE worker_bans 
                    SET is_active = 0 
                    WHERE worker_id = ? AND destination_id = ? AND is_active = 1
                ''', (worker_id, destination_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                conn.close()
                
                if rows_affected > 0:
                    self.logger.info(f"Cleared worker ban: worker={worker_id}, dest={destination_id}")
                    return True
                else:
                    self.logger.warning(f"No active ban found to clear: worker={worker_id}, dest={destination_id}")
                    return False
                
            except Exception as e:
                self.logger.error(f"Error clearing worker ban: {e}")
                return False

    async def get_banned_workers_summary(self) -> Dict[str, Any]:
        """Get a summary of all banned workers."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Get total active bans
                cursor.execute('SELECT COUNT(*) FROM worker_bans WHERE is_active = 1')
                total_bans = cursor.fetchone()[0]
                
                # Get bans by worker
                cursor.execute('''
                    SELECT worker_id, COUNT(*) as ban_count 
                    FROM worker_bans 
                    WHERE is_active = 1 
                    GROUP BY worker_id 
                    ORDER BY ban_count DESC
                ''')
                bans_by_worker = [{'worker_id': row[0], 'ban_count': row[1]} for row in cursor.fetchall()]
                
                # Get bans by destination
                cursor.execute('''
                    SELECT destination_id, COUNT(*) as ban_count 
                    FROM worker_bans 
                    WHERE is_active = 1 
                    GROUP BY destination_id 
                    ORDER BY ban_count DESC
                ''')
                bans_by_destination = [{'destination_id': row[0], 'ban_count': row[1]} for row in cursor.fetchall()]
                
                # Get bans by type
                cursor.execute('''
                    SELECT ban_type, COUNT(*) as ban_count 
                    FROM worker_bans 
                    WHERE is_active = 1 
                    GROUP BY ban_type 
                    ORDER BY ban_count DESC
                ''')
                bans_by_type = [{'ban_type': row[0], 'ban_count': row[1]} for row in cursor.fetchall()]
                
                conn.close()
                
                return {
                    'total_active_bans': total_bans,
                    'bans_by_worker': bans_by_worker,
                    'bans_by_destination': bans_by_destination,
                    'bans_by_type': bans_by_type
                }
                
            except Exception as e:
                self.logger.error(f"Error getting banned workers summary: {e}")
                return {
                    'total_active_bans': 0,
                    'bans_by_worker': [],
                    'bans_by_destination': [],
                    'bans_by_type': []
                }

    # ============================================================================
    # DESTINATION HEALTH METHODS
    # ============================================================================

    async def update_destination_health(self, destination_id: str, destination_name: str, 
                                      success: bool, error_message: str = None) -> bool:
        """Update destination health statistics after a posting attempt."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Check if destination exists
                cursor.execute('SELECT * FROM destination_health WHERE destination_id = ?', (destination_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    if success:
                        cursor.execute('''
                            UPDATE destination_health 
                            SET total_attempts = total_attempts + 1,
                                successful_posts = successful_posts + 1,
                                last_success = CURRENT_TIMESTAMP,
                                success_rate = (successful_posts + 1.0) / (total_attempts + 1.0) * 100,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE destination_id = ?
                        ''', (destination_id,))
                    else:
                        cursor.execute('''
                            UPDATE destination_health 
                            SET total_attempts = total_attempts + 1,
                                failed_posts = failed_posts + 1,
                                last_failure = CURRENT_TIMESTAMP,
                                success_rate = (successful_posts * 1.0) / (total_attempts + 1.0) * 100,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE destination_id = ?
                        ''', (destination_id,))
                else:
                    # Create new record
                    if success:
                        cursor.execute('''
                            INSERT INTO destination_health (
                                destination_id, destination_name, total_attempts, 
                                successful_posts, failed_posts, success_rate,
                                last_success, created_at, updated_at
                            ) VALUES (?, ?, 1, 1, 0, 100.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ''', (destination_id, destination_name))
                    else:
                        cursor.execute('''
                            INSERT INTO destination_health (
                                destination_id, destination_name, total_attempts, 
                                successful_posts, failed_posts, success_rate,
                                last_failure, created_at, updated_at
                            ) VALUES (?, ?, 1, 0, 1, 0.0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ''', (destination_id, destination_name))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Updated destination health: {destination_id}, success={success}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating destination health: {e}")
                return False

    async def get_destination_health(self, destination_id: str) -> Dict[str, Any]:
        """Get health statistics for a specific destination."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM destination_health WHERE destination_id = ?', (destination_id,))
                row = cursor.fetchone()
                
                if row:
                    health_data = dict(row)
                    conn.close()
                    return health_data
                else:
                    conn.close()
                    return {
                        'destination_id': destination_id,
                        'destination_name': destination_id,
                        'total_attempts': 0,
                        'successful_posts': 0,
                        'failed_posts': 0,
                        'success_rate': 100.0,
                        'last_success': None,
                        'last_failure': None,
                        'ban_count': 0,
                        'last_ban_time': None,
                        'cooldown_until': None
                    }
                
            except Exception as e:
                self.logger.error(f"Error getting destination health: {e}")
                return {}

    async def get_destination_success_rate(self, destination_id: str) -> float:
        """Get success rate for a specific destination."""
        health_data = await self.get_destination_health(destination_id)
        return health_data.get('success_rate', 100.0)

    async def get_problematic_destinations(self, min_failures: int = 3, max_success_rate: float = 50.0) -> List[Dict[str, Any]]:
        """Get destinations with poor performance."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM destination_health 
                    WHERE failed_posts >= ? AND success_rate <= ?
                    ORDER BY success_rate ASC, failed_posts DESC
                ''', (min_failures, max_success_rate))
                
                problematic = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                return problematic
                
            except Exception as e:
                self.logger.error(f"Error getting problematic destinations: {e}")
                return []

    async def get_destination_health_summary(self) -> Dict[str, Any]:
        """Get a summary of all destination health data."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                
                # Get total destinations
                cursor.execute('SELECT COUNT(*) FROM destination_health')
                total_destinations = cursor.fetchone()[0]
                
                # Get destinations by success rate
                cursor.execute('''
                    SELECT 
                        CASE 
                            WHEN success_rate >= 90 THEN 'excellent'
                            WHEN success_rate >= 75 THEN 'good'
                            WHEN success_rate >= 50 THEN 'fair'
                            ELSE 'poor'
                        END as health_category,
                        COUNT(*) as count
                    FROM destination_health 
                    GROUP BY health_category
                    ORDER BY 
                        CASE health_category
                            WHEN 'excellent' THEN 1
                            WHEN 'good' THEN 2
                            WHEN 'fair' THEN 3
                            WHEN 'poor' THEN 4
                        END
                ''')
                health_categories = [{'category': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
                # Get top performing destinations
                cursor.execute('''
                    SELECT destination_id, destination_name, success_rate, total_attempts
                    FROM destination_health 
                    WHERE total_attempts >= 5
                    ORDER BY success_rate DESC 
                    LIMIT 10
                ''')
                top_destinations = [{'destination_id': row[0], 'destination_name': row[1], 
                                   'success_rate': row[2], 'total_attempts': row[3]} for row in cursor.fetchall()]
                
                # Get worst performing destinations
                cursor.execute('''
                    SELECT destination_id, destination_name, success_rate, total_attempts
                    FROM destination_health 
                    WHERE total_attempts >= 3
                    ORDER BY success_rate ASC 
                    LIMIT 10
                ''')
                worst_destinations = [{'destination_id': row[0], 'destination_name': row[1], 
                                     'success_rate': row[2], 'total_attempts': row[3]} for row in cursor.fetchall()]
                
                # Get average success rate
                cursor.execute('SELECT AVG(success_rate) FROM destination_health WHERE total_attempts > 0')
                avg_success_rate = cursor.fetchone()[0] or 0
                
                conn.close()
                
                return {
                    'total_destinations': total_destinations,
                    'health_categories': health_categories,
                    'top_destinations': top_destinations,
                    'worst_destinations': worst_destinations,
                    'average_success_rate': round(avg_success_rate, 2)
                }
                
            except Exception as e:
                self.logger.error(f"Error getting destination health summary: {e}")
                return {
                    'total_destinations': 0,
                    'health_categories': [],
                    'top_destinations': [],
                    'worst_destinations': [],
                    'average_success_rate': 0
                }
