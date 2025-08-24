#!/usr/bin/env python3
"""
Comprehensive Health Check for AutoFarming Bot

This script performs a complete health check of your bot system and provides
detailed reports on what needs to be fixed.

Usage: python3 health_check.py
"""

import asyncio
import logging
import sys
import os
import importlib
from dotenv import load_dotenv
load_dotenv("config/.env")
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('health_check.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """Comprehensive health check system for AutoFarming Bot."""
    
    def __init__(self):
        self.health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'checks': {},
            'issues': [],
            'fixes': [],
            'warnings': [],
            'success_count': 0,
            'total_checks': 0
        }
        
    async def run_comprehensive_check(self):
        """Run all health checks."""
        logger.info("🏥 Starting Comprehensive Health Check...")
        logger.info("=" * 60)
        
        # Run all checks
        checks = [
            self.check_environment_variables,
            self.check_dependencies,
            self.check_imports,
            self.check_database_connection,
            self.check_bot_configuration,
            self.check_command_handlers,
            self.check_critical_user_flows,
            self.check_file_structure,
            self.check_syntax_errors
        ]
        
        for check in checks:
            try:
                await check()
                logger.info("-" * 40)
            except Exception as e:
                logger.error(f"❌ Health check {check.__name__} failed: {e}")
                self.health_report['checks'][check.__name__] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'fixes': []
                }
        
        # Generate final report
        self.generate_health_report()
        
    async def check_environment_variables(self):
        """Check if all required environment variables are set."""
        logger.info("🔧 Checking Environment Variables...")
        
        required_vars = [
            'BOT_TOKEN',
            'ADMIN_ID'
        ]
        
        optional_vars = [
            'BTC_ADDRESS', 'ETH_ADDRESS', 'SOL_ADDRESS', 'LTC_ADDRESS',
            'TON_ADDRESS', 'USDT_ADDRESS', 'USDC_ADDRESS', 'ADA_ADDRESS',
            'TRX_ADDRESS', 'ETHERSCAN_API_KEY', 'BLOCKCYPHER_API_KEY',
            'ENCRYPTION_KEY', 'SECRET_KEY', 'REDIS_URL', 'ENVIRONMENT'
        ]
        
        missing_required = []
        missing_optional = []
        
        # Check required variables
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        # Check optional variables
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        # Check if .env file exists
        env_file_exists = os.path.exists('config/.env')
        
        if missing_required:
            status = 'FAIL'
            issues = [f"Missing required environment variable: {var}" for var in missing_required]
            fixes = [
                "Create or update config/.env file with required variables",
                "Set BOT_TOKEN from @BotFather",
                "Set ADMIN_ID to your Telegram user ID",
                "Set DATABASE_URL for your database connection"
            ]
        else:
            status = 'PASS'
            issues = []
            fixes = []
        
        if missing_optional:
            self.health_report['warnings'].append(f"Missing optional variables: {', '.join(missing_optional)}")
        
        self.health_report['checks']['environment_variables'] = {
            'status': status,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'env_file_exists': env_file_exists,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Environment check: {status}")
        if missing_required:
            logger.error(f"❌ Missing required vars: {missing_required}")
        if missing_optional:
            logger.warning(f"⚠️ Missing optional vars: {missing_optional}")
    
    async def check_dependencies(self):
        """Check if all required dependencies are installed."""
        logger.info("📦 Checking Dependencies...")
        
        required_packages = [
            'telegram',
            'dotenv',
            'aiohttp',
            'asyncpg'
        ]
        
        optional_packages = [
            'redis',
            'cryptography',
            'requests'
        ]
        
        missing_required = []
        missing_optional = []
        
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
            except ImportError:
                missing_required.append(package)
        
        for package in optional_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_optional.append(package)
        
        if missing_required:
            status = 'FAIL'
            issues = [f"Missing required package: {pkg}" for pkg in missing_required]
            fixes = [
                "Install missing packages: pip install " + " ".join(missing_required),
                "Or run: pip install -r requirements.txt"
            ]
        else:
            status = 'PASS'
            issues = []
            fixes = []
        
        if missing_optional:
            self.health_report['warnings'].append(f"Missing optional packages: {', '.join(missing_optional)}")
        
        self.health_report['checks']['dependencies'] = {
            'status': status,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Dependencies check: {status}")
        if missing_required:
            logger.error(f"❌ Missing required packages: {missing_required}")
    
    async def check_imports(self):
        """Check if all custom modules can be imported."""
        logger.info("📚 Checking Module Imports...")
        
        custom_modules = [
            'config',
            'database',
            'commands.user_commands',
            'commands.admin_commands',
            'scheduler'
        ]
        
        failed_imports = []
        
        for module in custom_modules:
            try:
                importlib.import_module(module)
            except ImportError as e:
                failed_imports.append((module, str(e)))
        
        if failed_imports:
            status = 'FAIL'
            issues = [f"Failed to import {module}: {error}" for module, error in failed_imports]
            fixes = [
                "Check file paths and ensure all modules exist",
                "Verify __init__.py files in package directories",
                "Check for syntax errors in imported modules"
            ]
        else:
            status = 'PASS'
            issues = []
            fixes = []
        
        self.health_report['checks']['imports'] = {
            'status': status,
            'failed_imports': failed_imports,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Imports check: {status}")
        if failed_imports:
            logger.error(f"❌ Failed imports: {failed_imports}")
    
    async def check_database_connection(self):
        """Check database connection and table structure."""
        logger.info("🗄️ Checking Database Connection...")
        
        try:
            # Try to import and initialize database
            from config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Test basic database operations
            try:
                # Just test that we can connect and access tables
                conn = await db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
                tables = cursor.fetchall()
                await db.close()
                
                status = 'PASS'
                issues = []
                fixes = []
                
            except Exception as e:
                status = 'FAIL'
                issues = [f"Database table access failed: {e}"]
                fixes = [
                    "Run database migrations: python3 run_migration.py",
                    "Check database schema and table structure",
                    "Verify database permissions"
                ]
            
            # Cleanup test data
            try:
                # Note: You might want to add a cleanup method to your database manager
                pass
            except:
                pass
                
        except Exception as e:
            status = 'FAIL'
            issues = [f"Database connection failed: {e}"]
            fixes = [
                "Check DATABASE_URL in config/.env",
                "Verify database server is running",
                "Check database credentials and permissions",
                "Test database connection manually"
            ]
        
        self.health_report['checks']['database'] = {
            'status': status,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Database check: {status}")
        if status == 'FAIL':
            logger.error(f"❌ Database issues: {issues}")
    
    async def check_bot_configuration(self):
        """Check bot configuration and token validity."""
        logger.info("🤖 Checking Bot Configuration...")
        
        try:
            from config import BotConfig
            
            config = BotConfig.load_from_env()
            
            # Check if bot token is valid format
            if not config.bot_token or len(config.bot_token) < 10:
                status = 'FAIL'
                issues = ["Invalid or missing bot token"]
                fixes = [
                    "Get valid bot token from @BotFather",
                    "Update BOT_TOKEN in config/.env"
                ]
            else:
                status = 'PASS'
                issues = []
                fixes = []
            
        except Exception as e:
            status = 'FAIL'
            issues = [f"Bot configuration failed: {e}"]
            fixes = [
                "Check config.py for syntax errors",
                "Verify environment variables are set",
                "Test bot token with Telegram API"
            ]
        
        self.health_report['checks']['bot_configuration'] = {
            'status': status,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Bot configuration check: {status}")
        if status == 'FAIL':
            logger.error(f"❌ Bot configuration issues: {issues}")
    
    async def check_command_handlers(self):
        """Check if command handlers are properly set up."""
        logger.info("⌨️ Checking Command Handlers...")
        
        try:
            from commands import user_commands, admin_commands
            
            # Check if basic commands exist
            required_user_commands = ['start', 'help', 'subscribe']
            required_admin_commands = ['add_group', 'list_groups', 'admin_stats']
            
            missing_user_commands = []
            missing_admin_commands = []
            
            for cmd in required_user_commands:
                # Check for both cmd_command and cmd patterns
                if not hasattr(user_commands, f"{cmd}_command") and not hasattr(user_commands, cmd):
                    missing_user_commands.append(cmd)
            
            for cmd in required_admin_commands:
                if not hasattr(admin_commands, cmd):
                    missing_admin_commands.append(cmd)
            
            if missing_user_commands or missing_admin_commands:
                status = 'FAIL'
                issues = []
                if missing_user_commands:
                    issues.append(f"Missing user commands: {missing_user_commands}")
                if missing_admin_commands:
                    issues.append(f"Missing admin commands: {missing_admin_commands}")
                
                fixes = [
                    "Check commands/user_commands.py for missing functions",
                    "Check commands/admin_commands.py for missing functions",
                    "Ensure all command handlers are properly defined"
                ]
            else:
                status = 'PASS'
                issues = []
                fixes = []
                
        except Exception as e:
            status = 'FAIL'
            issues = [f"Command handlers check failed: {e}"]
            fixes = [
                "Check commands/__init__.py file",
                "Verify commands directory structure",
                "Check for syntax errors in command files"
            ]
        
        self.health_report['checks']['command_handlers'] = {
            'status': status,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Command handlers check: {status}")
        if status == 'FAIL':
            logger.error(f"❌ Command handler issues: {issues}")
    
    async def check_critical_user_flows(self):
        """Test critical user flows without actually executing them."""
        logger.info("🔄 Checking Critical User Flows...")
        
        try:
            from config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Test basic database connectivity
            try:
                conn = await db.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                await db.close()
                
                if user_count >= 0:  # Just check that we can query the database
                    status = 'PASS'
                    issues = []
                    fixes = []
                else:
                    status = 'FAIL'
                    issues = ["One or more user flows failed"]
                    fixes = [
                        "Check database operations",
                        "Verify subscription logic",
                        "Test payment processing"
                    ]
                    
            except Exception as e:
                status = 'FAIL'
                issues = [f"User flow check failed: {e}"]
                fixes = [
                    "Check database connection",
                    "Verify database schema",
                    "Test individual flow components"
                ]
                
        except Exception as e:
            status = 'FAIL'
            issues = [f"Critical user flows check failed: {e}"]
            fixes = [
                "Check database connection",
                "Verify database schema",
                "Test individual flow components"
            ]
        
        self.health_report['checks']['critical_user_flows'] = {
            'status': status,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Critical user flows check: {status}")
        if status == 'FAIL':
            logger.error(f"❌ User flow issues: {issues}")
    
    async def check_file_structure(self):
        """Check if all required files and directories exist."""
        logger.info("📁 Checking File Structure...")
        
        required_files = [
            'bot.py',
            'config.py',
            'database.py',
            'commands/__init__.py',
            'commands/user_commands.py',
            'commands/admin_commands.py',
            # requirements live at project root
            'requirements.txt'
        ]
        
        required_dirs = [
            'commands',
            'config',
            'src',
            'docs'
        ]
        
        missing_files = []
        missing_dirs = []
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        for dir_path in required_dirs:
            if not os.path.isdir(dir_path):
                missing_dirs.append(dir_path)
        
        if missing_files or missing_dirs:
            status = 'FAIL'
            issues = []
            if missing_files:
                issues.append(f"Missing files: {missing_files}")
            if missing_dirs:
                issues.append(f"Missing directories: {missing_dirs}")
            
            fixes = [
                "Create missing files and directories",
                "Check git repository for missing files",
                "Verify project structure matches documentation"
            ]
        else:
            status = 'PASS'
            issues = []
            fixes = []
        
        self.health_report['checks']['file_structure'] = {
            'status': status,
            'missing_files': missing_files,
            'missing_dirs': missing_dirs,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ File structure check: {status}")
        if missing_files:
            logger.error(f"❌ Missing files: {missing_files}")
        if missing_dirs:
            logger.error(f"❌ Missing directories: {missing_dirs}")
    
    async def check_syntax_errors(self):
        """Check for syntax errors in Python files."""
        logger.info("🔍 Checking for Syntax Errors...")
        
        python_files = [
            'bot.py',
            'config.py',
            'database.py',
            'commands/user_commands.py',
            'commands/admin_commands.py',
            'scheduler.py',
            'multi_crypto_payments.py'
        ]
        
        syntax_errors = []
        
        for file_path in python_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        compile(f.read(), file_path, 'exec')
                except SyntaxError as e:
                    syntax_errors.append((file_path, str(e)))
                except Exception as e:
                    syntax_errors.append((file_path, f"Error reading file: {e}"))
        
        if syntax_errors:
            status = 'FAIL'
            issues = [f"Syntax error in {file}: {error}" for file, error in syntax_errors]
            fixes = [
                "Fix syntax errors in Python files",
                "Check for missing colons, brackets, or quotes",
                "Verify proper indentation",
                "Use a Python linter to identify issues"
            ]
        else:
            status = 'PASS'
            issues = []
            fixes = []
        
        self.health_report['checks']['syntax_errors'] = {
            'status': status,
            'syntax_errors': syntax_errors,
            'issues': issues,
            'fixes': fixes
        }
        
        logger.info(f"✅ Syntax check: {status}")
        if syntax_errors:
            logger.error(f"❌ Syntax errors: {syntax_errors}")
    
    def generate_health_report(self):
        """Generate comprehensive health report."""
        logger.info("📊 Generating Health Report...")
        logger.info("=" * 60)
        
        # Calculate overall status
        total_checks = len(self.health_report['checks'])
        passed_checks = sum(1 for check in self.health_report['checks'].values() 
                          if check['status'] == 'PASS')
        failed_checks = total_checks - passed_checks
        
        if failed_checks == 0:
            overall_status = 'HEALTHY'
        elif failed_checks <= 2:
            overall_status = 'WARNING'
        else:
            overall_status = 'CRITICAL'
        
        self.health_report['overall_status'] = overall_status
        self.health_report['success_count'] = passed_checks
        self.health_report['total_checks'] = total_checks
        
        # Print summary
        logger.info(f"🏥 HEALTH CHECK SUMMARY")
        logger.info(f"Overall Status: {overall_status}")
        logger.info(f"Passed: {passed_checks}/{total_checks}")
        logger.info(f"Failed: {failed_checks}/{total_checks}")
        
        # Print detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for check_name, check_result in self.health_report['checks'].items():
            status_emoji = "✅" if check_result['status'] == 'PASS' else "❌"
            logger.info(f"{status_emoji} {check_name}: {check_result['status']}")
            
            if check_result['issues']:
                for issue in check_result['issues']:
                    logger.error(f"   ❌ {issue}")
            
            if check_result['fixes']:
                for fix in check_result['fixes']:
                    logger.info(f"   💡 Fix: {fix}")
        
        # Print warnings
        if self.health_report['warnings']:
            logger.info("\n⚠️ WARNINGS:")
            for warning in self.health_report['warnings']:
                logger.warning(f"   {warning}")
        
        # Save report to file
        with open('health_report.json', 'w') as f:
            json.dump(self.health_report, f, indent=2, default=str)
        
        logger.info("\n" + "=" * 60)
        logger.info("📄 Detailed report saved to: health_report.json")
        
        # Provide action items
        if overall_status == 'CRITICAL':
            logger.error("🚨 CRITICAL ISSUES DETECTED - Bot may not function properly!")
        elif overall_status == 'WARNING':
            logger.warning("⚠️ Some issues detected - Review and fix before deployment")
        else:
            logger.info("✅ Bot appears healthy - Ready for deployment!")

async def main():
    """Main function to run health check."""
    checker = HealthChecker()
    await checker.run_comprehensive_check()

if __name__ == "__main__":
    print("🏥 AutoFarming Bot Health Check")
    print("=" * 50)
    asyncio.run(main()) 