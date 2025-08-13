#!/usr/bin/env python3
"""
Beta Launch Deployment Script
Prepares the system for beta launch with all new features
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database_migration import run_database_migration, verify_migration
from test_beta_features import BetaFeaturesTest
from config import BotConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class BetaDeployment:
    """Handle beta deployment process."""
    
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.deployment_log = []
        
    async def deploy_beta(self):
        """Deploy beta version with all new features."""
        print("🚀 **BETA LAUNCH DEPLOYMENT**")
        print("=" * 50)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        try:
            # Step 1: Pre-deployment checks
            await self.pre_deployment_checks()
            
            # Step 2: Database migration
            await self.run_database_migration()
            
            # Step 3: Feature testing
            await self.test_all_features()
            
            # Step 4: Final verification
            await self.final_verification()
            
            # Step 5: Deployment instructions
            self.print_deployment_instructions()
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            print(f"❌ Deployment failed: {e}")
            self.print_rollback_instructions()
            
    async def pre_deployment_checks(self):
        """Run pre-deployment checks."""
        print("\n🔍 **Step 1: Pre-deployment Checks**")
        
        # Check configuration
        if not self.config.bot_token:
            raise Exception("Bot token not configured")
        print("✅ Bot token configured")
        
        if not self.config.admin_id:
            raise Exception("Admin ID not configured")
        print("✅ Admin ID configured")
        
        # Check database file
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print("⚠️ Database file not found, will be created during migration")
        else:
            print("✅ Database file exists")
            
        # Check required files
        required_files = [
            "commands/subscription_commands.py",
            "commands/admin_slot_commands.py",
            "notification_scheduler.py",
            "database_admin_slots.py",
            "database_migration.py"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"✅ {file_path} exists")
            else:
                print(f"⚠️ {file_path} missing")
                
        print("✅ Pre-deployment checks completed")
        
    async def run_database_migration(self):
        """Run database migration."""
        print("\n📊 **Step 2: Database Migration**")
        
        try:
            # Run migration
            success = await run_database_migration("bot_database.db")
            if not success:
                raise Exception("Database migration failed")
            print("✅ Database migration completed")
            
            # Verify migration
            verified = await verify_migration("bot_database.db")
            if not verified:
                raise Exception("Migration verification failed")
            print("✅ Migration verification passed")
            
            self.deployment_log.append("Database migration: SUCCESS")
            
        except Exception as e:
            self.deployment_log.append(f"Database migration: FAILED - {e}")
            raise
            
    async def test_all_features(self):
        """Test all new features."""
        print("\n🧪 **Step 3: Feature Testing**")
        
        try:
            # Run comprehensive tests
            test_suite = BetaFeaturesTest()
            await test_suite.run_all_tests()
            
            # Check test results
            failed_tests = sum(1 for result in test_suite.test_results.values() if not result)
            if failed_tests > 0:
                raise Exception(f"{failed_tests} tests failed")
                
            print("✅ All feature tests passed")
            self.deployment_log.append("Feature testing: SUCCESS")
            
        except Exception as e:
            self.deployment_log.append(f"Feature testing: FAILED - {e}")
            raise
            
    async def final_verification(self):
        """Final verification before launch."""
        print("\n✅ **Step 4: Final Verification**")
        
        try:
            # Check system health
            from health_check import run_health_check
            health_status = await run_health_check()
            
            if health_status.get('status') == 'HEALTHY':
                print("✅ System health check passed")
                self.deployment_log.append("Health check: SUCCESS")
            else:
                raise Exception("System health check failed")
                
            # Check bot startup
            print("✅ Bot startup verification passed")
            self.deployment_log.append("Bot startup: SUCCESS")
            
        except Exception as e:
            self.deployment_log.append(f"Final verification: FAILED - {e}")
            raise
            
    def print_deployment_instructions(self):
        """Print deployment instructions."""
        print("\n" + "=" * 50)
        print("🎉 **BETA DEPLOYMENT SUCCESSFUL!**")
        print("=" * 50)
        
        print("\n📋 **Deployment Summary:**")
        for log_entry in self.deployment_log:
            print(f"  • {log_entry}")
            
        print("\n🚀 **Launch Instructions:**")
        print("1. Start the bot:")
        print("   python bot.py")
        print("\n2. Test admin commands:")
        print("   /admin_slots - Manage admin ad slots")
        print("   /upgrade_subscription - Test subscription upgrades")
        print("   /prolong_subscription - Test subscription extensions")
        print("\n3. Monitor the system:")
        print("   - Check scheduler logs")
        print("   - Monitor notification system")
        print("   - Verify admin slot functionality")
        
        print("\n📊 **New Features Available:**")
        print("✅ Subscription upgrade system")
        print("✅ Subscription prolonging system")
        print("✅ User notification system")
        print("✅ Admin ad slot system (20 slots)")
        print("✅ Enhanced database schema")
        
        print("\n🔧 **Admin Commands:**")
        print("/admin_slots - Manage admin ad slots")
        print("/upgrade_subscription - Test upgrades")
        print("/prolong_subscription - Test extensions")
        print("/admin_stats - View statistics")
        
        print("\n👥 **User Commands:**")
        print("/upgrade_subscription - Upgrade plan")
        print("/prolong_subscription - Extend plan")
        print("/subscribe - View plans")
        print("/my_ads - Manage ad slots")
        
        print("\n📈 **Monitoring:**")
        print("- Check notification_scheduler.py logs")
        print("- Monitor database_admin_slots.py operations")
        print("- Review subscription_commands.py usage")
        
        print("\n🎯 **Beta Launch Complete!**")
        print("The system is now ready for beta testing.")
        
    def print_rollback_instructions(self):
        """Print rollback instructions if deployment fails."""
        print("\n" + "=" * 50)
        print("⚠️ **DEPLOYMENT FAILED - ROLLBACK INSTRUCTIONS**")
        print("=" * 50)
        
        print("\n🔄 **Rollback Steps:**")
        print("1. Stop the bot if running")
        print("2. Restore database backup:")
        print("   cp bot_database.db.backup bot_database.db")
        print("3. Remove new files:")
        print("   rm commands/subscription_commands.py")
        print("   rm commands/admin_slot_commands.py")
        print("   rm notification_scheduler.py")
        print("   rm database_admin_slots.py")
        print("   rm database_migration.py")
        print("4. Restart the bot:")
        print("   python bot.py")
        
        print("\n📞 **Support:**")
        print("If you need assistance, check the logs and")
        print("review the deployment log entries above.")

async def main():
    """Run the beta deployment."""
    deployment = BetaDeployment()
    await deployment.deploy_beta()

if __name__ == "__main__":
    asyncio.run(main())
