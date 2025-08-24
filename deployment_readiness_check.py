#!/usr/bin/env python3
"""
Deployment Readiness Check
Comprehensive verification of all bot functions before deployment
"""

import asyncio
import sys
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("deployment_check")

class DeploymentReadinessChecker:
    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def log_success(self, test_name: str, message: str):
        """Log a successful test."""
        logger.info(f"✅ {test_name}: {message}")
        self.results['passed'].append(f"{test_name}: {message}")
        
    def log_failure(self, test_name: str, message: str):
        """Log a failed test."""
        logger.error(f"❌ {test_name}: {message}")
        self.results['failed'].append(f"{test_name}: {message}")
        
    def log_warning(self, test_name: str, message: str):
        """Log a warning."""
        logger.warning(f"⚠️ {test_name}: {message}")
        self.results['warnings'].append(f"{test_name}: {message}")

    async def check_syntax_errors(self):
        """Check for syntax errors in all Python files."""
        logger.info("🔍 Checking for syntax errors...")
        
        try:
            # Check main files
            import subprocess
            
            files_to_check = [
                'bot.py',
                'src/services/payment_processor.py',
                'src/payment_address_direct_fix.py',
                'src/commands/payment_commands.py',
                'src/payment_timeout.py',
                'scheduler/__main__.py',
                'scheduler/core/scheduler.py',
                'scheduler/core/posting_service.py'
            ]
            
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    result = subprocess.run(
                        ['python3', '-m', 'py_compile', file_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.log_success("Syntax Check", f"{file_path} compiles successfully")
                    else:
                        self.log_failure("Syntax Check", f"{file_path} has syntax errors: {result.stderr}")
                else:
                    self.log_warning("Syntax Check", f"{file_path} not found")
                    
        except Exception as e:
            self.log_failure("Syntax Check", f"Error checking syntax: {e}")

    async def check_database_integrity(self):
        """Check database structure and integrity."""
        logger.info("🔍 Checking database integrity...")
        
        try:
            db_path = "bot_database.db"
            if not os.path.exists(db_path):
                self.log_failure("Database", "Database file not found")
                return
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check required tables
            required_tables = [
                'users', 'ad_slots', 'slot_destinations', 'payments',
                'admin_ad_slots', 'managed_groups', 'worker_cooldowns'
            ]
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    self.log_success("Database", f"Table {table} exists")
                else:
                    self.log_failure("Database", f"Required table {table} missing")
            
            # Check data integrity
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            self.log_success("Database", f"Found {user_count} users")
            
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
            active_slots = cursor.fetchone()[0]
            self.log_success("Database", f"Found {active_slots} active ad slots")
            
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
            active_admin_slots = cursor.fetchone()[0]
            self.log_success("Database", f"Found {active_admin_slots} active admin slots")
            
            conn.close()
            
        except Exception as e:
            self.log_failure("Database", f"Database check failed: {e}")

    async def check_environment_configuration(self):
        """Check environment variables and configuration."""
        logger.info("🔍 Checking environment configuration...")
        
        try:
            from dotenv import load_dotenv
            load_dotenv('config/.env')
            
            required_vars = [
                'BOT_TOKEN',
                'WORKER_1_API_ID', 'WORKER_1_API_HASH', 'WORKER_1_PHONE'
            ]
            
            for var in required_vars:
                value = os.getenv(var)
                if value:
                    if 'TOKEN' in var or 'HASH' in var:
                        # Mask sensitive values
                        masked_value = value[:8] + "..." if len(value) > 8 else "***"
                        self.log_success("Environment", f"{var} is configured ({masked_value})")
                    else:
                        self.log_success("Environment", f"{var} is configured")
                else:
                    self.log_failure("Environment", f"Required environment variable {var} not set")
            
            # Check worker configuration
            worker_count = 0
            for i in range(1, 11):
                api_id = os.getenv(f'WORKER_{i}_API_ID')
                api_hash = os.getenv(f'WORKER_{i}_API_HASH')
                phone = os.getenv(f'WORKER_{i}_PHONE')
                if api_id and api_hash and phone:
                    worker_count += 1
                    
            self.log_success("Environment", f"Configured {worker_count} worker accounts")
            
        except Exception as e:
            self.log_failure("Environment", f"Environment check failed: {e}")

    async def check_posting_system(self):
        """Check posting system functionality."""
        logger.info("🔍 Checking posting system...")
        
        try:
            # Check if posting service can be imported
            from scheduler.core.posting_service import PostingService
            self.log_success("Posting System", "PostingService can be imported")
            
            # Check database manager
            from src.database.manager import DatabaseManager
            self.log_success("Posting System", "DatabaseManager can be imported")
            
            # Check worker configuration
            from scheduler.config.worker_config import WorkerConfig
            worker_config = WorkerConfig()
            workers = worker_config.load_workers_from_env()
            self.log_success("Posting System", f"Loaded {len(workers)} worker configurations")
            
            # Check if there are active slots due for posting
            db = DatabaseManager("bot_database.db", logger)
            await db.initialize()
            
            active_ads = await db.get_active_ads_to_send()
            self.log_success("Posting System", f"Found {len(active_ads)} active ads to send")
            
            # Check destinations
            if active_ads:
                for ad in active_ads[:3]:  # Check first 3 ads
                    slot_id = ad.get('id')
                    slot_type = ad.get('slot_type', 'user')
                    destinations = await db.get_slot_destinations(slot_id, slot_type)
                    self.log_success("Posting System", f"Slot {slot_id} has {len(destinations)} destinations")
            
        except Exception as e:
            self.log_failure("Posting System", f"Posting system check failed: {e}")

    async def check_payment_system(self):
        """Check payment system functionality."""
        logger.info("🔍 Checking payment system...")
        
        try:
            # Check payment processor
            from src.services.payment_processor import PaymentProcessor
            self.log_success("Payment System", "PaymentProcessor can be imported")
            
            # Check payment address fix
            from src.payment_address_direct_fix import fix_payment_data, get_payment_message
            self.log_success("Payment System", "Payment address functions can be imported")
            
            # Test payment data fix
            test_payment = {
                'crypto_type': 'BTC',
                'amount_crypto': 0.001,
                'amount_usd': 15,
                'payment_id': 'TEST_123'
            }
            
            fixed_payment = fix_payment_data(test_payment)
            if fixed_payment:
                self.log_success("Payment System", "Payment data fix function works")
            else:
                self.log_failure("Payment System", "Payment data fix function failed")
            
            # Test payment message generation
            message = get_payment_message(test_payment, "basic")
            if message and len(message) > 0:
                self.log_success("Payment System", "Payment message generation works")
            else:
                self.log_failure("Payment System", "Payment message generation failed")
                
        except Exception as e:
            self.log_failure("Payment System", f"Payment system check failed: {e}")

    async def check_scheduler_system(self):
        """Check scheduler system functionality."""
        logger.info("🔍 Checking scheduler system...")
        
        try:
            # Check scheduler imports
            from scheduler.core.scheduler import AutomatedScheduler
            from scheduler.config.scheduler_config import SchedulerConfig
            self.log_success("Scheduler System", "Scheduler components can be imported")
            
            # Check scheduler configuration
            config = SchedulerConfig()
            self.log_success("Scheduler System", "Scheduler configuration loaded")
            
            # Check worker client
            from scheduler.workers.worker_client import WorkerClient
            self.log_success("Scheduler System", "WorkerClient can be imported")
            
            # Check posting service
            from scheduler.core.posting_service import PostingService
            self.log_success("Scheduler System", "PostingService can be imported")
            
        except Exception as e:
            self.log_failure("Scheduler System", f"Scheduler system check failed: {e}")

    async def check_admin_functions(self):
        """Check admin command functions."""
        logger.info("🔍 Checking admin functions...")
        
        try:
            # Check admin commands
            from commands import admin_commands
            self.log_success("Admin Functions", "Admin commands can be imported")
            
            # Check if admin functions exist
            admin_functions = [
                'admin_stats', 'posting_service_status', 'system_check',
                'failed_groups', 'fix_user_subscription'
            ]
            
            for func_name in admin_functions:
                if hasattr(admin_commands, func_name):
                    self.log_success("Admin Functions", f"Function {func_name} exists")
                else:
                    self.log_warning("Admin Functions", f"Function {func_name} not found")
                    
        except Exception as e:
            self.log_failure("Admin Functions", f"Admin functions check failed: {e}")

    async def check_user_functions(self):
        """Check user command functions."""
        logger.info("🔍 Checking user functions...")
        
        try:
            # Check user commands
            from commands import user_commands
            self.log_success("User Functions", "User commands can be imported")
            
            # Check if user functions exist
            user_functions = [
                'start', 'help', 'subscribe', 'my_ads', 'analytics'
            ]
            
            for func_name in user_functions:
                if hasattr(user_commands, func_name):
                    self.log_success("User Functions", f"Function {func_name} exists")
                else:
                    self.log_warning("User Functions", f"Function {func_name} not found")
                    
        except Exception as e:
            self.log_failure("User Functions", f"User functions check failed: {e}")

    async def check_file_structure(self):
        """Check if all required files exist."""
        logger.info("🔍 Checking file structure...")
        
        required_files = [
            'bot.py',
            'start_bot.py',
            'config/.env',
            'src/database/manager.py',
            'src/services/payment_processor.py',
            'scheduler/__main__.py',
            'scheduler/core/scheduler.py',
            'commands/user_commands.py',
            'commands/admin_commands.py'
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                self.log_success("File Structure", f"{file_path} exists")
            else:
                self.log_failure("File Structure", f"{file_path} missing")

    async def check_service_startup(self):
        """Check if services can start without errors."""
        logger.info("🔍 Checking service startup...")
        
        try:
            # Check if services are currently running
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True
            )
            
            if 'start_bot.py' in result.stdout:
                self.log_success("Service Startup", "Bot startup script is running")
            else:
                self.log_warning("Service Startup", "Bot startup script not running")
                
            if 'scheduler' in result.stdout:
                self.log_success("Service Startup", "Scheduler is running")
            else:
                self.log_warning("Service Startup", "Scheduler not running")
                
        except Exception as e:
            self.log_failure("Service Startup", f"Service startup check failed: {e}")

    async def run_full_check(self):
        """Run all deployment readiness checks."""
        logger.info("🚀 Starting Deployment Readiness Check")
        logger.info("=" * 60)
        
        await self.check_syntax_errors()
        await self.check_database_integrity()
        await self.check_environment_configuration()
        await self.check_posting_system()
        await self.check_payment_system()
        await self.check_scheduler_system()
        await self.check_admin_functions()
        await self.check_user_functions()
        await self.check_file_structure()
        await self.check_service_startup()
        
        # Generate summary
        logger.info("=" * 60)
        logger.info("📊 DEPLOYMENT READINESS SUMMARY")
        logger.info("=" * 60)
        
        total_tests = len(self.results['passed']) + len(self.results['failed']) + len(self.results['warnings'])
        
        logger.info(f"✅ Passed: {len(self.results['passed'])}")
        logger.info(f"❌ Failed: {len(self.results['failed'])}")
        logger.info(f"⚠️ Warnings: {len(self.results['warnings'])}")
        logger.info(f"📈 Success Rate: {(len(self.results['passed']) / total_tests * 100):.1f}%")
        
        if self.results['failed']:
            logger.info("\n❌ FAILURES:")
            for failure in self.results['failed']:
                logger.info(f"  • {failure}")
                
        if self.results['warnings']:
            logger.info("\n⚠️ WARNINGS:")
            for warning in self.results['warnings']:
                logger.info(f"  • {warning}")
        
        # Deployment recommendation
        if len(self.results['failed']) == 0:
            logger.info("\n🎉 DEPLOYMENT READY!")
            logger.info("All critical checks passed. The bot is ready for deployment.")
        elif len(self.results['failed']) <= 2:
            logger.info("\n⚠️ DEPLOYMENT WITH CAUTION")
            logger.info("Some issues found. Review failures before deployment.")
        else:
            logger.info("\n❌ NOT READY FOR DEPLOYMENT")
            logger.info("Multiple critical issues found. Fix failures before deployment.")

async def main():
    """Main function."""
    checker = DeploymentReadinessChecker()
    await checker.run_full_check()

if __name__ == "__main__":
    asyncio.run(main())
