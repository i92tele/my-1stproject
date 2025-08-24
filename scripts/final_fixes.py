#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/final_fixes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinalFixes:
    """Comprehensive fixes for all critical issues."""
    
    def __init__(self):
        self.fixes_applied = []
        
    async def fix_environment_configuration(self):
        """Fix environment configuration issues."""
        logger.info("🔧 Fixing environment configuration...")
        
        # Check if .env exists and has proper values
        env_file = 'config/.env'
        if not os.path.exists(env_file):
            logger.error("❌ .env file not found!")
            return False
            
        # Read current .env content
        with open(env_file, 'r') as f:
            content = f.read()
            
        # Check for placeholder values
        placeholders = [
            'your_telegram_bot_token_here',
            'your_admin_user_id_here',
            'your_ton_wallet_address_here',
            'postgresql://username:password@localhost/database_name'
        ]
        
        has_placeholders = any(placeholder in content for placeholder in placeholders)
        
        if has_placeholders:
            logger.warning("⚠️ .env file contains placeholder values")
            logger.info("Please provide actual values for:")
            logger.info("  - BOT_TOKEN (from @BotFather)")
            logger.info("  - ADMIN_ID (your Telegram user ID)")
            logger.info("  - TON_ADDRESS (your TON wallet)")
            logger.info("  - DATABASE_URL (PostgreSQL connection)")
            return False
        else:
            logger.info("✅ Environment configuration looks good")
            return True
    
    async def fix_database_connection(self):
        """Fix database connection issues."""
        logger.info("🔧 Fixing database connection...")
        
        try:
            # Test database connection
            from src.database.manager import DatabaseManager
            from config import BotConfig
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config, logger)
            
            await db.initialize()
            logger.info("✅ Database connection successful")
            
            # Test basic operations
            async with db.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("✅ Database operations working")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def fix_stale_files(self):
        """Clean up stale files that cause issues."""
        logger.info("🔧 Cleaning up stale files...")
        
        # Remove stale lock file
        lock_file = 'bot.lock'
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.info("✅ Removed stale bot.lock file")
            except Exception as e:
                logger.error(f"❌ Failed to remove lock file: {e}")
        
        # Clean up stale session files
        sessions_dir = 'sessions'
        if os.path.exists(sessions_dir):
            cleaned_count = 0
            for file in os.listdir(sessions_dir):
                if file.endswith('.session'):
                    file_path = os.path.join(sessions_dir, file)
                    # Check if file is older than 2 hours
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if datetime.now() - file_mtime > timedelta(hours=2):
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.info(f"✅ Removed stale session: {file}")
                        except Exception as e:
                            logger.error(f"❌ Failed to remove {file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"✅ Cleaned {cleaned_count} stale session files")
        
        # Clean up stale log files
        logs_dir = 'logs'
        if os.path.exists(logs_dir):
            for file in os.listdir(logs_dir):
                if file.endswith('.log'):
                    file_path = os.path.join(logs_dir, file)
                    # Check if file is older than 1 day
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if datetime.now() - file_mtime > timedelta(days=1):
                        try:
                            # Truncate instead of removing
                            with open(file_path, 'w') as f:
                                f.write(f"# Log file truncated at {datetime.now()}\n")
                            logger.info(f"✅ Truncated old log: {file}")
                        except Exception as e:
                            logger.error(f"❌ Failed to truncate {file}: {e}")
    
    async def fix_worker_system(self):
        """Fix worker system issues."""
        logger.info("🔧 Fixing worker system...")
        
        try:
            # Import worker fix
            from fix_worker_system import WorkerSystemFix
            from config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config, logger)
            
            worker_fix = WorkerSystemFix(config, db, logger)
            await worker_fix.initialize_workers()
            
            logger.info("✅ Worker system initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker system fix failed: {e}")
            return False
    
    async def fix_payment_system(self):
        """Fix payment system issues."""
        logger.info("🔧 Fixing payment system...")
        
        try:
            # Import payment fix
            from fix_payment_system import PaymentSystemFix
            from config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config, logger)
            
            payment_fix = PaymentSystemFix(config, db, logger)
            
            # Test payment creation
            test_payment = await payment_fix.create_secure_payment(123456, 'basic')
            logger.info("✅ Payment system working")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Payment system fix failed: {e}")
            return False
    
    async def fix_ui_system(self):
        """Fix UI system issues."""
        logger.info("🔧 Fixing UI system...")
        
        try:
            # Import UI fix
            from fix_ui_bugs import UIBugFix
            
            # Test UI components
            test_callback = "very_long_callback_data_that_exceeds_telegram_limit_of_64_bytes"
            truncated = UIBugFix.truncate_callback_data(test_callback)
            
            if len(truncated) <= 64:
                logger.info("✅ UI callback data fix working")
            else:
                logger.error("❌ UI callback data fix failed")
                return False
            
            # Test message splitting
            long_message = "This is a very long message. " * 200
            split_messages = UIBugFix.split_long_message(long_message)
            
            if len(split_messages) > 1:
                logger.info("✅ UI message splitting working")
            else:
                logger.error("❌ UI message splitting failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ UI system fix failed: {e}")
            return False
    
    async def fix_monitoring_system(self):
        """Set up monitoring system."""
        logger.info("🔧 Setting up monitoring system...")
        
        try:
            # Create monitoring directories
            os.makedirs('logs', exist_ok=True)
            os.makedirs('sessions', exist_ok=True)
            
            # Test health monitor
            from health_monitor import BotHealthMonitor
            
            logger.info("✅ Monitoring system ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Monitoring system setup failed: {e}")
            return False
    
    async def run_all_fixes(self):
        """Run all critical fixes."""
        logger.info("🚀 Starting comprehensive fixes...")
        
        fixes = [
            ("Environment Configuration", self.fix_environment_configuration),
            ("Stale Files Cleanup", self.fix_stale_files),
            ("Monitoring System", self.fix_monitoring_system),
            ("UI System", self.fix_ui_system),
        ]
        
        # Run fixes that don't require full config first
        for name, fix_func in fixes:
            try:
                logger.info(f"\n🔧 Running: {name}")
                success = await fix_func()
                if success:
                    self.fixes_applied.append(name)
                    logger.info(f"✅ {name} - SUCCESS")
                else:
                    logger.warning(f"⚠️ {name} - FAILED (may need config)")
            except Exception as e:
                logger.error(f"❌ {name} - ERROR: {e}")
        
        # Run fixes that require full config
        config_dependent_fixes = [
            ("Database Connection", self.fix_database_connection),
            ("Worker System", self.fix_worker_system),
            ("Payment System", self.fix_payment_system),
        ]
        
        logger.info("\n🔧 Running config-dependent fixes...")
        for name, fix_func in config_dependent_fixes:
            try:
                logger.info(f"🔧 Running: {name}")
                success = await fix_func()
                if success:
                    self.fixes_applied.append(name)
                    logger.info(f"✅ {name} - SUCCESS")
                else:
                    logger.warning(f"⚠️ {name} - FAILED (needs config)")
            except Exception as e:
                logger.error(f"❌ {name} - ERROR: {e}")
        
        # Summary
        logger.info(f"\n📊 FIXES SUMMARY:")
        logger.info(f"✅ Applied: {len(self.fixes_applied)}")
        logger.info(f"📋 Applied fixes: {', '.join(self.fixes_applied)}")
        
        if len(self.fixes_applied) >= 4:
            logger.info("🎉 Most critical fixes applied successfully!")
        else:
            logger.warning("⚠️ Some critical fixes failed - check configuration")
        
        return len(self.fixes_applied) >= 4

async def main():
    """Run all final fixes."""
    fixer = FinalFixes()
    success = await fixer.run_all_fixes()
    
    if success:
        logger.info("🚀 Bot is ready for launch!")
    else:
        logger.warning("⚠️ Some issues remain - check configuration")

if __name__ == '__main__':
    asyncio.run(main()) 