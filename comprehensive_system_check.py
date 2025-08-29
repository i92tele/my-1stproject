#!/usr/bin/env python3
"""
Comprehensive System Check
Check for bugs, problems, and issues in the entire bot system
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemChecker:
    """Comprehensive system checker for the bot."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def add_issue(self, category, message):
        """Add a critical issue."""
        self.issues.append(f"[{category}] {message}")
    
    def add_warning(self, category, message):
        """Add a warning."""
        self.warnings.append(f"[{category}] {message}")
    
    def add_success(self, category, message):
        """Add a success."""
        self.successes.append(f"[{category}] {message}")
    
    async def check_environment(self):
        """Check environment configuration."""
        print("🔍 CHECKING ENVIRONMENT")
        print("=" * 50)
        
        # Check required environment variables
        required_vars = [
            'BOT_TOKEN', 'ADMIN_ID', 'BTC_ADDRESS', 'ETH_ADDRESS', 
            'TON_ADDRESS', 'SOL_ADDRESS', 'LTC_ADDRESS'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.add_issue("ENV", f"Missing required variables: {', '.join(missing_vars)}")
        else:
            self.add_success("ENV", "All required environment variables present")
        
        # Check API keys
        api_keys = [
            'BLOCKCYPHER_API_KEY', 'ETHERSCAN_API_KEY', 'SOLSCAN_API_KEY',
            'BLOCKCHAIN_INFO_API_KEY', 'MEMPOOL_API_KEY', 'BLOCKSTREAM_API_KEY'
        ]
        
        configured_apis = []
        for api in api_keys:
            if os.getenv(api):
                configured_apis.append(api)
        
        if len(configured_apis) >= 3:
            self.add_success("APIS", f"Good API coverage: {len(configured_apis)} APIs configured")
        else:
            self.add_warning("APIS", f"Limited API coverage: only {len(configured_apis)} APIs configured")
    
    async def check_database(self):
        """Check database health."""
        print("\n🔍 CHECKING DATABASE")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get connection
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Check all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'users', 'payments', 'subscriptions', 'ad_slots', 
                'workers', 'destinations', 'slot_destinations'
            ]
            
            missing_tables = []
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)
            
            if missing_tables:
                self.add_issue("DB", f"Missing tables: {', '.join(missing_tables)}")
            else:
                self.add_success("DB", "All required tables present")
            
            # Check data integrity
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
            active_slots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            active_subs = cursor.fetchone()[0]
            
            if active_workers == 0:
                self.add_issue("DB", "No active workers found")
            else:
                self.add_success("DB", f"{active_workers} active workers")
            
            if active_slots == 0:
                self.add_warning("DB", "No active ad slots found")
            else:
                self.add_success("DB", f"{active_slots} active ad slots")
            
            if active_subs == 0:
                self.add_warning("DB", "No active subscriptions found")
            else:
                self.add_success("DB", f"{active_subs} active subscriptions")
            
            await db.close()
            
        except Exception as e:
            self.add_issue("DB", f"Database error: {e}")
    
    async def check_payment_system(self):
        """Check payment system health."""
        print("\n🔍 CHECKING PAYMENT SYSTEM")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Check supported cryptos
            supported_cryptos = list(processor.supported_cryptos.keys())
            self.add_success("PAYMENTS", f"Supported cryptos: {', '.join(supported_cryptos)}")
            
            # Check pending payments
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
            pending_payments = cursor.fetchone()[0]
            
            if pending_payments > 0:
                self.add_warning("PAYMENTS", f"{pending_payments} pending payments")
            else:
                self.add_success("PAYMENTS", "No pending payments")
            
            # Check expired payments
            cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'expired'")
            expired_payments = cursor.fetchone()[0]
            
            if expired_payments > 10:
                self.add_warning("PAYMENTS", f"{expired_payments} expired payments (consider cleanup)")
            
            await db.close()
            
        except Exception as e:
            self.add_issue("PAYMENTS", f"Payment system error: {e}")
    
    async def check_scheduler(self):
        """Check scheduler health."""
        print("\n🔍 CHECKING SCHEDULER")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Check scheduler components
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
            active_admin_slots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations WHERE is_active = 1")
            active_destinations = cursor.fetchone()[0]
            
            if active_workers > 0 and active_admin_slots > 0 and active_destinations > 0:
                self.add_success("SCHEDULER", "Scheduler ready to post")
                self.add_success("SCHEDULER", f"Capacity: {active_workers} workers × {active_destinations} destinations")
            else:
                if active_workers == 0:
                    self.add_issue("SCHEDULER", "No active workers")
                if active_admin_slots == 0:
                    self.add_issue("SCHEDULER", "No active admin slots")
                if active_destinations == 0:
                    self.add_issue("SCHEDULER", "No active destinations")
            
            await db.close()
            
        except Exception as e:
            self.add_issue("SCHEDULER", f"Scheduler error: {e}")
    
    async def check_security(self):
        """Check security issues."""
        print("\n🔍 CHECKING SECURITY")
        print("=" * 50)
        
        # Check for hardcoded secrets
        sensitive_files = [
            'config/.env', 'multi_crypto_payments.py', 'src/config/main_config.py'
        ]
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    # Check for hardcoded tokens
                    if 'your_' in content and 'token' in content.lower():
                        self.add_warning("SECURITY", f"Potential placeholder in {file_path}")
                    
                    # Check for exposed API keys
                    if len(content) > 1000 and 'api_key' in content.lower():
                        self.add_warning("SECURITY", f"Large file with API keys: {file_path}")
                        
                except Exception:
                    pass
        
        self.add_success("SECURITY", "Basic security checks completed")
    
    async def check_performance(self):
        """Check performance issues."""
        print("\n🔍 CHECKING PERFORMANCE")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            # Check database size
            cursor.execute("SELECT COUNT(*) FROM workers")
            worker_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM payments")
            payment_count = cursor.fetchone()[0]
            
            if worker_count > 100:
                self.add_warning("PERFORMANCE", f"Large worker table: {worker_count} records")
            
            if payment_count > 1000:
                self.add_warning("PERFORMANCE", f"Large payment table: {payment_count} records")
            
            # Check for old data
            cursor.execute("SELECT COUNT(*) FROM payments WHERE created_at < datetime('now', '-30 days')")
            old_payments = cursor.fetchone()[0]
            
            if old_payments > 100:
                self.add_warning("PERFORMANCE", f"Consider cleaning {old_payments} old payments")
            
            await db.close()
            
        except Exception as e:
            self.add_issue("PERFORMANCE", f"Performance check error: {e}")
    
    def print_summary(self):
        """Print summary of all issues."""
        print("\n📊 SYSTEM CHECK SUMMARY")
        print("=" * 50)
        
        if self.successes:
            print("\n✅ SUCCESSES:")
            for success in self.successes:
                print(f"  {success}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.issues:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.issues:
                print(f"  {issue}")
        
        print(f"\n📈 SCORE: {len(self.successes)} ✅, {len(self.warnings)} ⚠️, {len(self.issues)} ❌")
        
        if len(self.issues) == 0:
            print("\n🎉 SYSTEM IS HEALTHY!")
        elif len(self.issues) <= 2:
            print("\n🔧 MINOR ISSUES - FIX RECOMMENDED")
        else:
            print("\n🚨 MULTIPLE ISSUES - IMMEDIATE ATTENTION REQUIRED")

async def main():
    """Main function."""
    checker = SystemChecker()
    
    await checker.check_environment()
    await checker.check_database()
    await checker.check_payment_system()
    await checker.check_scheduler()
    await checker.check_security()
    await checker.check_performance()
    
    checker.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
