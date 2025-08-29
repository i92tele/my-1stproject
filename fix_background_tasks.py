#!/usr/bin/env python3
"""
Background Task Fixes
Fix background tasks with proper error recovery, resource cleanup, and concurrent access
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

class BackgroundTaskFixer:
    """Fix background task issues."""
    
    def __init__(self):
        self.task_registry = {}
        self.max_retries = 3
        self.retry_delay = 60  # seconds
    
    async def fix_payment_monitoring(self):
        """Fix payment monitoring background task."""
        print("🔧 Fixing payment monitoring...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create payment monitoring task table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_monitoring_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    task_type TEXT DEFAULT 'payment_verification',
                    status TEXT DEFAULT 'running',
                    last_run_at TIMESTAMP,
                    next_run_at TIMESTAMP,
                    run_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create payment monitoring logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_monitoring_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    payment_id TEXT,
                    verification_attempt INTEGER DEFAULT 0,
                    success BOOLEAN,
                    error_message TEXT,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_monitoring_tasks_id ON payment_monitoring_tasks(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_monitoring_tasks_status ON payment_monitoring_tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_monitoring_tasks_next_run ON payment_monitoring_tasks(next_run_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_monitoring_logs_task ON payment_monitoring_logs(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_monitoring_logs_payment ON payment_monitoring_logs(payment_id)")
            
            conn.commit()
            await db.close()
            
            print("✅ Fixed payment monitoring")
            
        except Exception as e:
            print(f"❌ Error fixing payment monitoring: {e}")
    
    async def add_task_error_recovery(self):
        """Add comprehensive task error recovery."""
        print("🔧 Adding task error recovery...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create task error recovery table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_error_recovery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    error_type TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    last_retry_at TIMESTAMP,
                    next_retry_at TIMESTAMP,
                    recovery_strategy TEXT DEFAULT 'exponential_backoff',
                    is_resolved BOOLEAN DEFAULT 0,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create task health monitoring table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_health_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    health_status TEXT DEFAULT 'healthy',
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    heartbeat_interval_seconds INTEGER DEFAULT 300,
                    missed_heartbeats INTEGER DEFAULT 0,
                    max_missed_heartbeats INTEGER DEFAULT 3,
                    is_alive BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(task_id)
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_error_recovery_task ON task_error_recovery(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_error_recovery_resolved ON task_error_recovery(is_resolved)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_error_recovery_next_retry ON task_error_recovery(next_retry_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_health_monitoring_task ON task_health_monitoring(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_health_monitoring_alive ON task_health_monitoring(is_alive)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_health_monitoring_heartbeat ON task_health_monitoring(last_heartbeat)")
            
            conn.commit()
            await db.close()
            
            print("✅ Added task error recovery")
            
        except Exception as e:
            print(f"❌ Error adding task error recovery: {e}")
    
    async def implement_resource_cleanup(self):
        """Implement proper resource cleanup for background tasks."""
        print("🔧 Implementing resource cleanup...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create resource tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    released_at TIMESTAMP,
                    is_allocated BOOLEAN DEFAULT 1,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create resource cleanup logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resource_cleanup_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    cleanup_type TEXT NOT NULL,
                    resources_cleaned INTEGER DEFAULT 0,
                    cleanup_duration_ms INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    cleaned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_tracking_task ON resource_tracking(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_tracking_allocated ON resource_tracking(is_allocated)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_tracking_type ON resource_tracking(resource_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_cleanup_logs_task ON resource_cleanup_logs(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_cleanup_logs_type ON resource_cleanup_logs(cleanup_type)")
            
            conn.commit()
            await db.close()
            
            print("✅ Implemented resource cleanup")
            
        except Exception as e:
            print(f"❌ Error implementing resource cleanup: {e}")
    
    async def add_concurrent_access_protection(self):
        """Add concurrent access protection for background tasks."""
        print("🔧 Adding concurrent access protection...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create task locks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_locks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lock_key TEXT UNIQUE NOT NULL,
                    task_id TEXT NOT NULL,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    lock_type TEXT DEFAULT 'exclusive',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create task coordination table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_coordination (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coordination_id TEXT UNIQUE NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    participants_count INTEGER DEFAULT 0,
                    max_participants INTEGER DEFAULT 1,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_locks_key ON task_locks(lock_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_locks_active ON task_locks(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_locks_expires ON task_locks(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_coordination_id ON task_coordination(coordination_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_coordination_status ON task_coordination(status)")
            
            conn.commit()
            await db.close()
            
            print("✅ Added concurrent access protection")
            
        except Exception as e:
            print(f"❌ Error adding concurrent access protection: {e}")
    
    async def add_task_monitoring(self):
        """Add comprehensive task monitoring."""
        print("🔧 Adding task monitoring...")
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Create task metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    metric_unit TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create task alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    alert_level TEXT DEFAULT 'info',
                    alert_message TEXT,
                    is_acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create task performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    success BOOLEAN,
                    error_count INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_metrics_task ON task_metrics(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_metrics_name ON task_metrics(metric_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_metrics_recorded ON task_metrics(recorded_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_alerts_task ON task_alerts(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_alerts_type ON task_alerts(alert_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_alerts_level ON task_alerts(alert_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_performance_task ON task_performance(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_performance_executed ON task_performance(executed_at)")
            
            conn.commit()
            await db.close()
            
            print("✅ Added task monitoring")
            
        except Exception as e:
            print(f"❌ Error adding task monitoring: {e}")
    
    async def fix_all_background_issues(self):
        """Fix all background task issues."""
        print("🔧 COMPREHENSIVE BACKGROUND TASK FIX")
        print("=" * 50)
        
        await self.fix_payment_monitoring()
        await self.add_task_error_recovery()
        await self.implement_resource_cleanup()
        await self.add_concurrent_access_protection()
        await self.add_task_monitoring()
        
        print("\n✅ All background task fixes completed!")

async def main():
    """Main function."""
    fixer = BackgroundTaskFixer()
    await fixer.fix_all_background_issues()

if __name__ == "__main__":
    asyncio.run(main())
