#!/usr/bin/env python3
"""
Simple AutoFarming Bot Project Cleanup
Fixes the most critical issues without complex path operations
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleCleanup:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "backups" / "simple_cleanup_backup"
        self.files_removed = []
        self.files_moved = []
        
    def run_cleanup(self):
        """Run the simplified cleanup process."""
        logger.info("🚀 Starting simple AutoFarming Bot cleanup...")
        
        try:
            # Step 1: Create backup
            self.create_simple_backup()
            
            # Step 2: Remove obvious duplicates
            self.remove_obvious_duplicates()
            
            # Step 3: Remove unused files
            self.remove_unused_files()
            
            # Step 4: Create main.py entry point
            self.create_main_entry_point()
            
            # Step 5: Generate report
            self.generate_report()
            
            logger.info("✅ Simple cleanup completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            raise
    
    def create_simple_backup(self):
        """Create a simple backup of important files."""
        logger.info("💾 Creating simple backup...")
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup important files
        important_files = [
            'bot.py',
            'database.py',
            'config.py',
            'requirements.txt'
        ]
        
        for file_name in important_files:
            if os.path.exists(file_name):
                shutil.copy2(file_name, self.backup_dir / file_name)
        
        logger.info(f"✅ Backup created at {self.backup_dir}")
    
    def remove_obvious_duplicates(self):
        """Remove obvious duplicate files."""
        logger.info("🗑️ Removing obvious duplicates...")
        
        # List of obvious duplicates to remove
        duplicates_to_remove = [
            # Multiple startup scripts
            'start_bot.py',
            'start_bot_safe.py', 
            'start_lightweight.py',
            'start_simple.py',
            'start_services.py',
            'start_all_services.py',
            
            # Multiple payment files
            'ton_payments.py',
            'multi_crypto_payments.py',
            'crypto_payments.py',
            'improved_ton_payments.py',
            'enhance_crypto_payments.py',
            'enhanced_crypto_payments.py',
            
            # Multiple worker files
            'fix_worker_system.py',
            'fix_worker_config.py',
            'fix_worker_bans.py',
            'final_worker_cleanup.py',
            'remove_frozen_workers.py',
            'restore_all_workers.py',
            'cleanup_banned_workers.py',
            'add_workers.py',
            'add_more_workers.py',
            
            # Multiple scheduler files
            'scheduler.py',
            'scheduler_backup.py',
            'fix_scheduler_stuck.py',
            
            # Multiple test files
            'test_bot_status.py',
            'run_integration_tests.py',
            'comprehensive_test_suite.py',
            
            # Multiple utility files
            'simple_cleanup.py',
            'merge_databases.py',
            'database_migration.py',
            'run_migration.py',
            'update_ton_address.py',
            'update_multisig_config.py',
            'payment_monitor.py',
            'quick_worker_status.py',
            'check_payments.py',
            'check_worker_status.py',
            'activate_subscription.py',
            'analytics.py',
            'check_banned_workers.py',
            'referral_system.py',
            'monetization.py',
            'enhanced_admin.py',
            'enhanced_config.py',
            'enhanced_ui.py',
            'final_fixes.py',
            'fix_payment_system.py',
            'fix_ton_qr.py',
            'fix_ui_bugs.py',
            'deploy_critical_fixes.py',
            'diagnose_payment.py',
            'diagnose_stuck.py',
            'content_moderation.py',
            'create_test_payment.py',
            'security.py',
            'maintenance.py',
            'get_telegram_credentials.py'
        ]
        
        for file_name in duplicates_to_remove:
            if os.path.exists(file_name):
                try:
                    # Move to backup instead of deleting
                    backup_path = self.backup_dir / file_name
                    shutil.move(file_name, backup_path)
                    self.files_removed.append(file_name)
                    logger.info(f"Removed duplicate: {file_name}")
                except Exception as e:
                    logger.warning(f"Could not remove {file_name}: {e}")
    
    def remove_unused_files(self):
        """Remove obviously unused files."""
        logger.info("🗑️ Removing unused files...")
        
        unused_files = [
            'cleanup.log',
            'scheduler.log',
            'test_integration.log',
            'health_check.log',
            'health_report.json',
            'worker_session.session',
            'bot_database.db',
            'sqlite_methods.txt',
            'postgresql_methods.txt',
            'HEALTH_CHECK_README.md',
            'TEST_INTEGRATION_README.md',
            'activate_env.sh',
            'setup.sh',
            'start_all_services.sh',
            'stop_all.sh',
            'deploy.sh',
            'docker-compose.yml'
        ]
        
        for file_name in unused_files:
            if os.path.exists(file_name):
                try:
                    # Move to backup instead of deleting
                    backup_path = self.backup_dir / file_name
                    shutil.move(file_name, backup_path)
                    self.files_removed.append(file_name)
                    logger.info(f"Removed unused: {file_name}")
                except Exception as e:
                    logger.warning(f"Could not remove {file_name}: {e}")
    
    def create_main_entry_point(self):
        """Create a simple main.py entry point."""
        logger.info("📝 Creating main.py entry point...")
        
        main_content = '''#!/usr/bin/env python3
"""
AutoFarming Bot - Main Entry Point
Simple entry point for the AutoFarming Bot
"""

import asyncio
import logging
from src.bot import main as bot_main

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main entry point for the AutoFarming Bot."""
    try:
        await bot_main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        with open('main.py', 'w') as f:
            f.write(main_content)
        
        self.files_moved.append('main.py')
        logger.info("✅ Created main.py entry point")
    
    def generate_report(self):
        """Generate a simple cleanup report."""
        logger.info("📊 Generating cleanup report...")
        
        report_content = f"""# Simple Cleanup Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Files removed: {len(self.files_removed)}
- Files created: {len(self.files_moved)}
- Backup location: {self.backup_dir}

## Files Removed
{chr(10).join(f"- {file}" for file in self.files_removed)}

## Files Created
{chr(10).join(f"- {file}" for file in self.files_moved)}

## Next Steps
1. Test the new main.py entry point: `python3 main.py`
2. Verify all imports work correctly
3. Configure environment variables
4. Run health checks

## Backup Location
All removed files are available in: {self.backup_dir}
"""
        
        with open('SIMPLE_CLEANUP_REPORT.md', 'w') as f:
            f.write(report_content)
        
        logger.info("✅ Cleanup report generated: SIMPLE_CLEANUP_REPORT.md")

def main():
    """Main function."""
    cleanup = SimpleCleanup()
    cleanup.run_cleanup()

if __name__ == "__main__":
    main() 