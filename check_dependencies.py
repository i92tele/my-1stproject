#!/usr/bin/env python3
"""
Dependency Check Script
Verifies all dependencies and integrations for the beta features
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import BotConfig
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class DependencyChecker:
    """Check all dependencies and integrations."""
    
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager("bot_database.db", logger)
        self.check_results = {}
        
    async def check_all_dependencies(self):
        """Check all dependencies and integrations."""
        print("🔍 **DEPENDENCY CHECK FOR BETA FEATURES**")
        print("=" * 50)
        
        try:
            # Initialize database
            await self.db.initialize()
            print("✅ Database initialized")
            
            # Check 1: File Dependencies
            await self.check_file_dependencies()
            
            # Check 2: Import Dependencies
            await self.check_import_dependencies()
            
            # Check 3: Database Schema Dependencies
            await self.check_database_dependencies()
            
            # Check 4: Bot Integration Dependencies
            await self.check_bot_integration()
            
            # Check 5: Callback Handler Dependencies
            await self.check_callback_dependencies()
            
            # Print results
            self.print_check_results()
            
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            print(f"❌ Dependency check failed: {e}")
            
    async def check_file_dependencies(self):
        """Check if all required files exist."""
        print("\n📁 **Check 1: File Dependencies**")
        
        required_files = [
            "commands/subscription_commands.py",
            "commands/admin_slot_commands.py",
            "notification_scheduler.py",
            "database_admin_slots.py",
            "database_migration.py",
            "test_beta_features.py",
            "deploy_beta.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"✅ {file_path} exists")
            else:
                print(f"❌ {file_path} missing")
                missing_files.append(file_path)
        
        self.check_results['file_dependencies'] = len(missing_files) == 0
        
        if missing_files:
            print(f"⚠️ Missing files: {missing_files}")
            
    async def check_import_dependencies(self):
        """Check if all imports work correctly."""
        print("\n📦 **Check 2: Import Dependencies**")
        
        import_checks = [
            ("commands.subscription_commands", "subscription_commands"),
            ("commands.admin_slot_commands", "admin_slot_commands"),
            ("notification_scheduler", "NotificationScheduler"),
            ("database_admin_slots", "AdminSlotDatabase"),
            ("database_migration", "run_database_migration")
        ]
        
        failed_imports = []
        for module_name, item_name in import_checks:
            try:
                module = __import__(module_name, fromlist=[item_name])
                if hasattr(module, item_name):
                    print(f"✅ {module_name}.{item_name} imports successfully")
                else:
                    print(f"❌ {module_name}.{item_name} not found in module")
                    failed_imports.append(f"{module_name}.{item_name}")
            except ImportError as e:
                print(f"❌ Failed to import {module_name}.{item_name}: {e}")
                failed_imports.append(f"{module_name}.{item_name}")
            except Exception as e:
                print(f"❌ Error importing {module_name}.{item_name}: {e}")
                failed_imports.append(f"{module_name}.{item_name}")
        
        self.check_results['import_dependencies'] = len(failed_imports) == 0
        
        if failed_imports:
            print(f"⚠️ Failed imports: {failed_imports}")
            
    async def check_database_dependencies(self):
        """Check database schema and methods."""
        print("\n🗄️ **Check 3: Database Dependencies**")
        
        # Check if new database methods exist
        required_methods = [
            'upgrade_user_subscription',
            'extend_user_subscription',
            'create_admin_ad_slots',
            'get_admin_ad_slots',
            'get_admin_ad_slot',
            'update_admin_slot_content',
            'update_admin_slot_destinations',
            'update_admin_slot_status',
            'get_admin_slot_destinations',
            'get_admin_slots_stats'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if hasattr(self.db, method_name):
                print(f"✅ Database method {method_name} exists")
            else:
                print(f"❌ Database method {method_name} missing")
                missing_methods.append(method_name)
        
        self.check_results['database_dependencies'] = len(missing_methods) == 0
        
        if missing_methods:
            print(f"⚠️ Missing database methods: {missing_methods}")
            
    async def check_bot_integration(self):
        """Check bot integration dependencies."""
        print("\n🤖 **Check 4: Bot Integration Dependencies**")
        
        # Check bot.py imports
        bot_file = "bot.py"
        if os.path.exists(bot_file):
            with open(bot_file, 'r') as f:
                content = f.read()
                
            required_imports = [
                "from commands import subscription_commands",
                "from commands import admin_slot_commands",
                "SUBSCRIPTION_COMMANDS_AVAILABLE",
                "ADMIN_SLOT_COMMANDS_AVAILABLE"
            ]
            
            missing_imports = []
            for import_line in required_imports:
                if import_line in content:
                    print(f"✅ Bot import: {import_line}")
                else:
                    print(f"❌ Bot import missing: {import_line}")
                    missing_imports.append(import_line)
            
            # Check command registration
            required_commands = [
                "upgrade_subscription",
                "prolong_subscription",
                "admin_slots"
            ]
            
            missing_commands = []
            for command in required_commands:
                if f'CommandHandler("{command}"' in content:
                    print(f"✅ Bot command registered: {command}")
                else:
                    print(f"❌ Bot command missing: {command}")
                    missing_commands.append(command)
            
            self.check_results['bot_integration'] = len(missing_imports) == 0 and len(missing_commands) == 0
            
            if missing_imports or missing_commands:
                print(f"⚠️ Missing bot integrations: {missing_imports + missing_commands}")
        else:
            print("❌ bot.py file not found")
            self.check_results['bot_integration'] = False
            
    async def check_callback_dependencies(self):
        """Check callback handler dependencies."""
        print("\n🔄 **Check 5: Callback Handler Dependencies**")
        
        # Check bot.py callback routing
        bot_file = "bot.py"
        if os.path.exists(bot_file):
            with open(bot_file, 'r') as f:
                content = f.read()
                
            required_callbacks = [
                "upgrade:",
                "prolong:",
                "check_upgrade_payment:",
                "check_prolong_payment:",
                "admin_slot:",
                "admin_quick_post",
                "admin_post_slot:",
                "admin_set_content:",
                "admin_set_destinations:",
                "admin_toggle_slot:",
                "admin_slot_stats",
                "admin_slots_refresh"
            ]
            
            missing_callbacks = []
            for callback in required_callbacks:
                if callback in content:
                    print(f"✅ Callback routing: {callback}")
                else:
                    print(f"❌ Callback routing missing: {callback}")
                    missing_callbacks.append(callback)
            
            # Check notification scheduler integration
            if "NotificationScheduler" in content and "notification_scheduler" in content:
                print("✅ Notification scheduler integration found")
            else:
                print("❌ Notification scheduler integration missing")
                missing_callbacks.append("notification_scheduler_integration")
            
            self.check_results['callback_dependencies'] = len(missing_callbacks) == 0
            
            if missing_callbacks:
                print(f"⚠️ Missing callback routing: {missing_callbacks}")
        else:
            print("❌ bot.py file not found")
            self.check_results['callback_dependencies'] = False
            
    def print_check_results(self):
        """Print dependency check results."""
        print("\n" + "=" * 50)
        print("📊 **DEPENDENCY CHECK RESULTS**")
        print("=" * 50)
        
        total_checks = len(self.check_results)
        passed_checks = sum(1 for result in self.check_results.values() if result)
        failed_checks = total_checks - passed_checks
        
        print(f"**Total Checks:** {total_checks}")
        print(f"**Passed:** {passed_checks}")
        print(f"**Failed:** {failed_checks}")
        print(f"**Success Rate:** {(passed_checks/total_checks)*100:.1f}%")
        
        print("\n**Detailed Results:**")
        for check_name, result in self.check_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {check_name}: {status}")
        
        if failed_checks == 0:
            print("\n🎉 **ALL DEPENDENCIES SATISFIED!**")
            print("✅ Beta features are ready for deployment!")
        else:
            print(f"\n⚠️ **{failed_checks} DEPENDENCIES MISSING**")
            print("Please fix the missing dependencies before deployment.")
            
        print("\n📋 **Next Steps:**")
        if failed_checks == 0:
            print("1. Run database migration: python database_migration.py")
            print("2. Test features: python test_beta_features.py")
            print("3. Deploy: python deploy_beta.py")
            print("4. Start bot: python bot.py")
        else:
            print("1. Fix missing dependencies listed above")
            print("2. Re-run dependency check")
            print("3. Proceed with deployment once all checks pass")

async def main():
    """Run the dependency check."""
    checker = DependencyChecker()
    await checker.check_all_dependencies()

if __name__ == "__main__":
    asyncio.run(main())
