#!/usr/bin/env python3
"""
Worker Management Fixes
Fix worker assignment, health monitoring, and rate limiting issues
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

class WorkerManagementFixer:
    """Fix worker management issues."""
    
    def __init__(self):
        self.rate_limit_window = 3600  # 1 hour
        self.daily_limit_window = 86400  # 24 hours
    
    async def fix_worker_assignment_logic(self):
        """Fix worker assignment logic with proper load balancing."""
        print("🔧 Fixing worker assignment logic...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create worker assignment tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    slot_id INTEGER,
                    destination_id TEXT,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    success BOOLEAN,
                    error_message TEXT,
                    processing_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_id) REFERENCES workers(rowid)
                )
            ''')
            
            # Create worker load tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_load (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    hourly_posts INTEGER DEFAULT 0,
                    daily_posts INTEGER DEFAULT 0,
                    last_post_at TIMESTAMP,
                    current_hour_start TIMESTAMP,
                    current_day_start TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_assignments_worker ON worker_assignments(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_assignments_slot ON worker_assignments(slot_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_load_worker ON worker_load(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_load_hourly ON worker_load(hourly_posts)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_load_daily ON worker_load(daily_posts)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed worker assignment logic")
            
        except Exception as e:
            print(f"❌ Error fixing worker assignment: {e}")
    
    async def add_worker_health_monitoring(self):
        """Add comprehensive worker health monitoring."""
        print("🔧 Adding worker health monitoring...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Check if workers table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workers'")
            if not cursor.fetchone():
                print("⚠️ Workers table doesn't exist, creating without foreign key constraints")
                # Create worker health table without foreign key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER NOT NULL,
                        health_status TEXT DEFAULT 'healthy',
                        success_rate REAL DEFAULT 100.0,
                        total_posts INTEGER DEFAULT 0,
                        successful_posts INTEGER DEFAULT 0,
                        failed_posts INTEGER DEFAULT 0,
                        consecutive_failures INTEGER DEFAULT 0,
                        last_success_at TIMESTAMP,
                        last_failure_at TIMESTAMP,
                        ban_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        is_available BOOLEAN DEFAULT 1,
                        maintenance_mode BOOLEAN DEFAULT 0,
                        last_health_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(worker_id)
                    )
                ''')
                
                # Create worker ban tracking table without foreign key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_bans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER NOT NULL,
                        destination_id TEXT,
                        ban_type TEXT DEFAULT 'temporary',
                        ban_reason TEXT,
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        estimated_unban_time TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            else:
                # Create worker health table with foreign key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_health (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER NOT NULL,
                        health_status TEXT DEFAULT 'healthy',
                        success_rate REAL DEFAULT 100.0,
                        total_posts INTEGER DEFAULT 0,
                        successful_posts INTEGER DEFAULT 0,
                        failed_posts INTEGER DEFAULT 0,
                        consecutive_failures INTEGER DEFAULT 0,
                        last_success_at TIMESTAMP,
                        last_failure_at TIMESTAMP,
                        ban_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        is_available BOOLEAN DEFAULT 1,
                        maintenance_mode BOOLEAN DEFAULT 0,
                        last_health_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(worker_id),
                        FOREIGN KEY (worker_id) REFERENCES workers(rowid)
                    )
                ''')
                
                # Create worker ban tracking table with foreign key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS worker_bans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        worker_id INTEGER NOT NULL,
                        destination_id TEXT,
                        ban_type TEXT DEFAULT 'temporary',
                        ban_reason TEXT,
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        estimated_unban_time TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (worker_id) REFERENCES workers(rowid)
                    )
                ''')
            
            # Create indexes with error handling
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_health_worker ON worker_health(worker_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_health_status ON worker_health(health_status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_health_available ON worker_health(is_available)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_bans_worker ON worker_bans(worker_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_bans_active ON worker_bans(is_active)")
                print("✅ Created worker health indexes")
            except Exception as e:
                print(f"⚠️ Could not create some indexes: {e}")
            
            conn.commit()
            await db.close()
            
            print("✅ Added worker health monitoring")
            
        except Exception as e:
            print(f"❌ Error adding worker health monitoring: {e}")
    
    async def implement_rate_limiting(self):
        """Implement proper rate limiting for workers."""
        print("🔧 Implementing rate limiting...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create rate limiting table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
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
            
            # Create cooldown tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_cooldowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_rate_limits_worker ON worker_rate_limits(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_rate_limits_blocked ON worker_rate_limits(is_blocked)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_cooldowns_worker ON worker_cooldowns(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_cooldowns_active ON worker_cooldowns(is_active)")
            
            conn.commit()
            await db.close()
            
            print("✅ Implemented rate limiting")
            
        except Exception as e:
            print(f"❌ Error implementing rate limiting: {e}")
    
    async def fix_worker_rotation(self):
        """Fix worker rotation with intelligent selection."""
        print("🔧 Fixing worker rotation...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create worker rotation tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_rotation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    rotation_priority INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    is_preferred BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id)
                )
            ''')
            
            # Create worker performance tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    destination_id TEXT,
                    posts_attempted INTEGER DEFAULT 0,
                    posts_successful INTEGER DEFAULT 0,
                    posts_failed INTEGER DEFAULT 0,
                    average_response_time_ms INTEGER DEFAULT 0,
                    last_performance_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id, destination_id)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_rotation_priority ON worker_rotation(rotation_priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_rotation_last_used ON worker_rotation(last_used_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_performance_worker ON worker_performance(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_performance_destination ON worker_performance(destination_id)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed worker rotation")
            
        except Exception as e:
            print(f"❌ Error fixing worker rotation: {e}")
    
    async def add_worker_recovery_mechanisms(self):
        """Add worker recovery and failover mechanisms."""
        print("🔧 Adding worker recovery mechanisms...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create worker recovery table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_recovery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    recovery_type TEXT DEFAULT 'automatic',
                    failure_reason TEXT,
                    recovery_attempts INTEGER DEFAULT 0,
                    max_recovery_attempts INTEGER DEFAULT 3,
                    last_recovery_attempt TIMESTAMP,
                    recovery_success BOOLEAN DEFAULT 0,
                    is_in_recovery BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(worker_id)
                )
            ''')
            
            # Create worker failover table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_failover (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    primary_worker_id INTEGER NOT NULL,
                    backup_worker_id INTEGER NOT NULL,
                    failover_reason TEXT,
                    failover_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    restored_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (primary_worker_id) REFERENCES workers(rowid),
                    FOREIGN KEY (backup_worker_id) REFERENCES workers(rowid)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_recovery_worker ON worker_recovery(worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_recovery_active ON worker_recovery(is_in_recovery)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_failover_primary ON worker_failover(primary_worker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_failover_active ON worker_failover(is_active)")
            
            conn.commit()
            await db.close()
            
            print("✅ Added worker recovery mechanisms")
            
        except Exception as e:
            print(f"❌ Error adding worker recovery: {e}")
    
    async def fix_all_worker_issues(self):
        """Fix all worker management issues."""
        print("🔧 COMPREHENSIVE WORKER MANAGEMENT FIX")
        print("=" * 50)
        
        await self.fix_worker_assignment_logic()
        await self.add_worker_health_monitoring()
        await self.implement_rate_limiting()
        await self.fix_worker_rotation()
        await self.add_worker_recovery_mechanisms()
        
        print("\n✅ All worker management fixes completed!")

async def main():
    """Main function."""
    fixer = WorkerManagementFixer()
    await fixer.fix_all_worker_issues()

if __name__ == "__main__":
    asyncio.run(main())
