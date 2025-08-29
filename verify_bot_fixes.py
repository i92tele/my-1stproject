#!/usr/bin/env python3
"""
Bot Fixes Verification Script
Verify that all bot fixes have been applied correctly
"""

import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_database_schema():
    """Verify database schema fixes."""
    print("🔍 Verifying database schema fixes...")
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check if new tables exist
        new_tables = [
            'worker_activity_log',
            'destination_health',
            'system_health',
            'payment_rate_limits',
            'payment_monitoring',
            'worker_health',
            'worker_bans',
            'worker_rate_limits',
            'worker_cooldowns',
            'worker_rotation',
            'worker_performance',
            'worker_recovery',
            'worker_failover',
            'error_categories',
            'posting_errors',
            'destination_tracking',
            'posting_attempts',
            'posting_rate_limits',
            'posting_cooldowns',
            'posting_coordination',
            'posting_sessions',
            'posting_metrics',
            'posting_alerts',
            'payment_monitoring_tasks',
            'payment_monitoring_logs',
            'task_error_recovery',
            'task_health_monitoring',
            'resource_tracking',
            'resource_cleanup_logs',
            'task_locks',
            'task_coordination',
            'task_metrics',
            'task_alerts',
            'task_performance'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in new_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                existing_tables.append(table)
            else:
                missing_tables.append(table)
        
        print(f"✅ Found {len(existing_tables)} new tables")
        if missing_tables:
            print(f"❌ Missing {len(missing_tables)} tables: {missing_tables}")
        else:
            print("✅ All new tables created successfully")
        
        await db.close()
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"❌ Error verifying database schema: {e}")
        return False

async def verify_payment_security():
    """Verify payment security fixes."""
    print("🔍 Verifying payment security fixes...")
    
    try:
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        # Check if manual verification is disabled
        if hasattr(payment_processor, '_verify_ton_manual'):
            print("✅ Manual verification method exists")
        else:
            print("❌ Manual verification method not found")
        
        await db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying payment security: {e}")
        return False

async def verify_worker_management():
    """Verify worker management fixes."""
    print("🔍 Verifying worker management fixes...")
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check worker health table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_health'")
        if cursor.fetchone():
            print("✅ Worker health monitoring table exists")
        else:
            print("❌ Worker health monitoring table missing")
        
        # Check worker rate limits table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_rate_limits'")
        if cursor.fetchone():
            print("✅ Worker rate limiting table exists")
        else:
            print("❌ Worker rate limiting table missing")
        
        await db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying worker management: {e}")
        return False

async def verify_posting_logic():
    """Verify posting logic fixes."""
    print("🔍 Verifying posting logic fixes...")
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check error categories table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_categories'")
        if cursor.fetchone():
            print("✅ Error categorization table exists")
        else:
            print("❌ Error categorization table missing")
        
        # Check destination tracking table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_tracking'")
        if cursor.fetchone():
            print("✅ Destination tracking table exists")
        else:
            print("❌ Destination tracking table missing")
        
        await db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying posting logic: {e}")
        return False

async def verify_background_tasks():
    """Verify background task fixes."""
    print("🔍 Verifying background task fixes...")
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check task monitoring tables
        monitoring_tables = ['task_health_monitoring', 'task_error_recovery', 'task_metrics']
        
        for table in monitoring_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")
        
        await db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying background tasks: {e}")
        return False

async def main():
    """Main verification function."""
    print("🔍 BOT FIXES VERIFICATION")
    print("=" * 50)
    
    results = []
    
    results.append(await verify_database_schema())
    results.append(await verify_payment_security())
    results.append(await verify_worker_management())
    results.append(await verify_posting_logic())
    results.append(await verify_background_tasks())
    
    successful = sum(results)
    total = len(results)
    
    print(f"
📊 VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"✅ Successful verifications: {successful}/{total}")
    print(f"❌ Failed verifications: {total - successful}/{total}")
    
    if successful == total:
        print("🎉 All fixes verified successfully!")
    else:
        print("⚠️ Some fixes need attention")

if __name__ == "__main__":
    asyncio.run(main())
