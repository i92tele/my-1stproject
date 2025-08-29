#!/usr/bin/env python3
"""
Posting Logic Fixes
Fix posting logic with proper error handling, destination tracking, and rate limiting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PostingLogicFixer:
    """Fix posting logic issues."""
    
    def __init__(self):
        self.error_categories = {
            'invalid_destination': 'Destination does not exist or bot not member',
            'rate_limited': 'Rate limit exceeded for destination',
            'authentication_failed': 'Worker authentication failed',
            'content_restricted': 'Content violates channel rules',
            'network_error': 'Network connection error',
            'permission_denied': 'Bot lacks permission to post',
            'channel_full': 'Channel is full or archived',
            'user_banned': 'User is banned from channel',
            'unknown_error': 'Unknown error occurred'
        }
    
    async def fix_error_handling(self):
        """Fix error handling with proper categorization."""
        print("🔧 Fixing error handling...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create error categorization table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_pattern TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    severity TEXT DEFAULT 'medium',
                    auto_retry BOOLEAN DEFAULT 1,
                    retry_delay_seconds INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(error_pattern)
                )
            ''')
            
            # Insert common error patterns
            error_patterns = [
                ('Invalid destination', 'invalid_destination', 'Destination does not exist or bot not member', 'high', 0, 0),
                ('Rate limit exceeded', 'rate_limited', 'Rate limit exceeded for destination', 'medium', 1, 3600),
                ('Authentication failed', 'authentication_failed', 'Worker authentication failed', 'high', 0, 0),
                ('Content restricted', 'content_restricted', 'Content violates channel rules', 'medium', 0, 0),
                ('Network error', 'network_error', 'Network connection error', 'low', 1, 60),
                ('Permission denied', 'permission_denied', 'Bot lacks permission to post', 'high', 0, 0),
                ('Channel is full', 'channel_full', 'Channel is full or archived', 'medium', 0, 0),
                ('User is banned', 'user_banned', 'User is banned from channel', 'high', 0, 0),
                ('Chat not found', 'invalid_destination', 'Destination does not exist', 'high', 0, 0),
                ('Forbidden', 'permission_denied', 'Bot lacks permission to post', 'high', 0, 0),
                ('Too many requests', 'rate_limited', 'Rate limit exceeded', 'medium', 1, 1800),
                ('Connection error', 'network_error', 'Network connection error', 'low', 1, 120),
                ('Timeout', 'network_error', 'Request timeout', 'low', 1, 60)
            ]
            
            for pattern, category, description, severity, auto_retry, retry_delay in error_patterns:
                cursor.execute('''
                    INSERT OR REPLACE INTO error_categories 
                    (error_pattern, category, description, severity, auto_retry, retry_delay_seconds)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (pattern, category, description, severity, auto_retry, retry_delay))
            
            # Create error tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    error_message TEXT,
                    error_category TEXT,
                    error_severity TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    next_retry_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers(rowid)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_categories_pattern ON error_categories(error_pattern)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_errors_category ON posting_errors(error_category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_errors_destination ON posting_errors(destination_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_errors_next_retry ON posting_errors(next_retry_at)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed error handling")
            
        except Exception as e:
            print(f"❌ Error fixing error handling: {e}")
    
    async def fix_destination_tracking(self):
        """Fix destination tracking with proper logging."""
        print("🔧 Fixing destination tracking...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create destination tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS destination_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    destination_id TEXT NOT NULL,
                    destination_name TEXT,
                    destination_type TEXT DEFAULT 'group',
                    total_attempts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    last_success_at TIMESTAMP,
                    last_failure_at TIMESTAMP,
                    consecutive_failures INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    rate_limited BOOLEAN DEFAULT 0,
                    rate_limit_expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(destination_id)
                )
            ''')
            
            # Create posting attempts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    slot_id INTEGER,
                    slot_type TEXT DEFAULT 'user',
                    attempt_number INTEGER DEFAULT 1,
                    success BOOLEAN,
                    error_message TEXT,
                    error_category TEXT,
                    response_time_ms INTEGER,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers(rowid)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_destination_tracking_id ON destination_tracking(destination_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_destination_tracking_success_rate ON destination_tracking(success_rate)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_destination_tracking_active ON destination_tracking(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_attempts_worker ON posting_attempts(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_attempts_destination ON posting_attempts(destination_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_attempts_success ON posting_attempts(success)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed destination tracking")
            
        except Exception as e:
            print(f"❌ Error fixing destination tracking: {e}")
    
    async def implement_rate_limiting(self):
        """Implement proper rate limiting for posting."""
        print("🔧 Implementing posting rate limiting...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create posting rate limits table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    rate_type TEXT DEFAULT 'hourly',
                    current_count INTEGER DEFAULT 0,
                    limit_value INTEGER DEFAULT 15,
                    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    window_end TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT 0,
                    blocked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id, destination_id, rate_type)
                )
            ''')
            
            # Create posting cooldowns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_cooldowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    cooldown_type TEXT DEFAULT 'post',
                    cooldown_duration_seconds INTEGER DEFAULT 60,
                    cooldown_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cooldown_end TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id, destination_id, cooldown_type)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_rate_limits_worker ON posting_rate_limits(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_rate_limits_destination ON posting_rate_limits(destination_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_rate_limits_blocked ON posting_rate_limits(is_blocked)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_cooldowns_worker ON posting_cooldowns(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_cooldowns_active ON posting_cooldowns(is_active)")
            
            conn.commit()
            await db.close()
            
            print("✅ Implemented posting rate limiting")
            
        except Exception as e:
            print(f"❌ Error implementing rate limiting: {e}")
    
    async def fix_parallel_posting(self):
        """Fix parallel posting with proper coordination."""
        print("🔧 Fixing parallel posting...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create posting coordination table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_coordination (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posting_session_id TEXT NOT NULL,
                    worker_id INTEGER,
                    slot_id INTEGER,
                    destination_id TEXT,
                    status TEXT DEFAULT 'pending',
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(posting_session_id, worker_id, destination_id)
                )
            ''')
            
            # Create posting sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    total_slots INTEGER DEFAULT 0,
                    total_destinations INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_coordination_session ON posting_coordination(posting_session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_coordination_worker ON posting_coordination(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_coordination_status ON posting_coordination(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_sessions_id ON posting_sessions(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_sessions_status ON posting_sessions(status)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed parallel posting")
            
        except Exception as e:
            print(f"❌ Error fixing parallel posting: {e}")
    
    async def add_posting_monitoring(self):
        """Add comprehensive posting monitoring."""
        print("🔧 Adding posting monitoring...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create posting metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    metric_value REAL,
                    metric_unit TEXT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    slot_id INTEGER,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create posting alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    alert_level TEXT DEFAULT 'info',
                    alert_message TEXT,
                    worker_id INTEGER,
                    destination_id TEXT,
                    slot_id INTEGER,
                    is_acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_metrics_type ON posting_metrics(metric_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_metrics_worker ON posting_metrics(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_metrics_recorded ON posting_metrics(recorded_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_alerts_type ON posting_alerts(alert_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_alerts_level ON posting_alerts(alert_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posting_alerts_acknowledged ON posting_alerts(is_acknowledged)")
            
            conn.commit()
            await db.close()
            
            print("✅ Added posting monitoring")
            
        except Exception as e:
            print(f"❌ Error adding posting monitoring: {e}")
    
    async def fix_all_posting_issues(self):
        """Fix all posting logic issues."""
        print("🔧 COMPREHENSIVE POSTING LOGIC FIX")
        print("=" * 50)
        
        await self.fix_error_handling()
        await self.fix_destination_tracking()
        await self.implement_rate_limiting()
        await self.fix_parallel_posting()
        await self.add_posting_monitoring()
        
        print("\n✅ All posting logic fixes completed!")

async def main():
    """Main function."""
    fixer = PostingLogicFixer()
    await fixer.fix_all_posting_issues()

if __name__ == "__main__":
    asyncio.run(main())
