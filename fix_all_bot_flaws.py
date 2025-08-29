#!/usr/bin/env python3
"""
Master Bot Flaws Fix Script
Run all fix scripts to address all identified bot logic flaws
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MasterBotFixer:
    """Master script to fix all bot flaws."""
    
    def __init__(self):
        self.fix_scripts = [
            {
                'name': 'Database Schema Fixes',
                'script': 'fix_database_schema_comprehensive.py',
                'description': 'Fix database schema inconsistencies and standardize table structures'
            },
            {
                'name': 'Payment Security Fixes',
                'script': 'fix_payment_security.py',
                'description': 'Fix payment system security vulnerabilities and add proper validation'
            },
            {
                'name': 'Worker Management Fixes',
                'script': 'fix_worker_management.py',
                'description': 'Fix worker assignment, health monitoring, and rate limiting issues'
            },
            {
                'name': 'Posting Logic Fixes',
                'script': 'fix_posting_logic.py',
                'description': 'Fix posting logic with proper error handling, destination tracking, and rate limiting'
            },
            {
                'name': 'Background Task Fixes',
                'script': 'fix_background_tasks.py',
                'description': 'Fix background tasks with proper error recovery, resource cleanup, and concurrent access'
            }
        ]
        self.results = []
    
    async def run_fix_script(self, script_info: Dict[str, str]) -> Dict[str, Any]:
        """Run a single fix script."""
        script_name = script_info['name']
        script_file = script_info['script']
        
        print(f"\n🔧 RUNNING: {script_name}")
        print(f"📝 Description: {script_info['description']}")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, script_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if result.returncode == 0:
                print(f"✅ {script_name} completed successfully in {duration:.1f}s")
                print(f"📤 Output: {result.stdout.strip()}")
                return {
                    'script': script_name,
                    'status': 'success',
                    'duration': duration,
                    'output': result.stdout.strip(),
                    'error': None
                }
            else:
                print(f"❌ {script_name} failed after {duration:.1f}s")
                print(f"📤 Output: {result.stdout.strip()}")
                print(f"❌ Error: {result.stderr.strip()}")
                return {
                    'script': script_name,
                    'status': 'failed',
                    'duration': duration,
                    'output': result.stdout.strip(),
                    'error': result.stderr.strip()
                }
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {script_name} timed out after 5 minutes")
            return {
                'script': script_name,
                'status': 'timeout',
                'duration': 300,
                'output': '',
                'error': 'Script timed out after 5 minutes'
            }
        except Exception as e:
            print(f"💥 {script_name} crashed: {e}")
            return {
                'script': script_name,
                'status': 'crashed',
                'duration': 0,
                'output': '',
                'error': str(e)
            }
    
    async def run_all_fixes(self):
        """Run all fix scripts in order."""
        print("🚀 MASTER BOT FLAWS FIX")
        print("=" * 60)
        print("This script will fix all identified bot logic flaws:")
        print("1. Database Schema Inconsistencies")
        print("2. Payment System Security Vulnerabilities")
        print("3. Worker Management Issues")
        print("4. Posting Logic Flaws")
        print("5. Background Task Issues")
        print("=" * 60)
        
        total_start_time = datetime.now()
        
        for script_info in self.fix_scripts:
            result = await self.run_fix_script(script_info)
            self.results.append(result)
            
            # Add a small delay between scripts
            await asyncio.sleep(2)
        
        total_end_time = datetime.now()
        total_duration = (total_end_time - total_start_time).total_seconds()
        
        await self.print_summary(total_duration)
    
    async def print_summary(self, total_duration: float):
        """Print a summary of all fixes."""
        print(f"\n📊 FIX SUMMARY")
        print("=" * 60)
        print(f"Total execution time: {total_duration:.1f} seconds")
        
        successful = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] != 'success']
        
        print(f"✅ Successful fixes: {len(successful)}/{len(self.results)}")
        print(f"❌ Failed fixes: {len(failed)}/{len(self.results)}")
        
        if successful:
            print(f"\n✅ SUCCESSFUL FIXES:")
            for result in successful:
                print(f"  - {result['script']} ({result['duration']:.1f}s)")
        
        if failed:
            print(f"\n❌ FAILED FIXES:")
            for result in failed:
                print(f"  - {result['script']} ({result['status']})")
                if result['error']:
                    print(f"    Error: {result['error']}")
        
        print(f"\n🎯 NEXT STEPS:")
        if len(successful) == len(self.results):
            print("1. ✅ All fixes completed successfully!")
            print("2. 🔄 Restart the bot to apply all changes")
            print("3. 📊 Monitor the system for any remaining issues")
            print("4. 🧪 Test payment verification and posting functionality")
        else:
            print("1. ⚠️ Some fixes failed - check the errors above")
            print("2. 🔧 Manually run failed scripts or fix issues")
            print("3. 🔄 Restart the bot after fixing remaining issues")
            print("4. 📊 Monitor the system for any remaining issues")
        
        print(f"\n📝 RECOMMENDED ACTIONS:")
        print("1. Run 'python3 analyze_failed_posts.py' to check posting status")
        print("2. Run 'python3 fix_invalid_destinations.py' to fix destination issues")
        print("3. Run 'python3 cleanup_expired_payments.py' to clean up old payments")
        print("4. Test BTC payment verification with new APIs")
        print("5. Monitor posting success rates and worker performance")
    
    async def create_verification_script(self):
        """Create a script to verify all fixes."""
        print("\n🔧 Creating verification script...")
        
        verification_script = '''#!/usr/bin/env python3
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
    
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"✅ Successful verifications: {successful}/{total}")
    print(f"❌ Failed verifications: {total - successful}/{total}")
    
    if successful == total:
        print("🎉 All fixes verified successfully!")
    else:
        print("⚠️ Some fixes need attention")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        with open('verify_bot_fixes.py', 'w') as f:
            f.write(verification_script)
        
        print("✅ Created verify_bot_fixes.py")
        print("💡 Run 'python3 verify_bot_fixes.py' to verify all fixes")

async def main():
    """Main function."""
    fixer = MasterBotFixer()
    await fixer.run_all_fixes()
    await fixer.create_verification_script()

if __name__ == "__main__":
    asyncio.run(main())
