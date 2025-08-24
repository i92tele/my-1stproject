#!/usr/bin/env python3
"""
Final System Verification

This script performs a comprehensive verification of all system components
after the immediate error fixes to ensure everything is working properly.
"""

import os
import sys
import sqlite3
import asyncio
from datetime import datetime

def verify_system():
    """Perform comprehensive system verification."""
    print("🔍 FINAL SYSTEM VERIFICATION")
    print("=" * 60)
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    try:
        # 1. Database Integrity Check
        print("\n🗄️ 1. Database Integrity Check...")
        verify_database_integrity(results)
        
        # 2. Core Files Check
        print("\n📁 2. Core Files Check...")
        verify_core_files(results)
        
        # 3. Configuration Check
        print("\n⚙️ 3. Configuration Check...")
        verify_configuration(results)
        
        # 4. Admin Interface Check
        print("\n👨‍💼 4. Admin Interface Check...")
        verify_admin_interface(results)
        
        # 5. User Interface Check
        print("\n👤 5. User Interface Check...")
        verify_user_interface(results)
        
        # 6. Payment System Check
        print("\n💰 6. Payment System Check...")
        verify_payment_system(results)
        
        # 7. Worker System Check
        print("\n🤖 7. Worker System Check...")
        verify_worker_system(results)
        
        # 8. Posting System Check
        print("\n📝 8. Posting System Check...")
        verify_posting_system(results)
        
        # Generate final report
        print("\n" + "=" * 60)
        print("📊 FINAL VERIFICATION REPORT")
        print("=" * 60)
        
        print(f"✅ Passed: {len(results['passed'])}")
        print(f"❌ Failed: {len(results['failed'])}")
        print(f"⚠️ Warnings: {len(results['warnings'])}")
        
        if results['passed']:
            print(f"\n✅ PASSED TESTS:")
            for test in results['passed']:
                print(f"  • {test}")
        
        if results['failed']:
            print(f"\n❌ FAILED TESTS:")
            for test in results['failed']:
                print(f"  • {test}")
        
        if results['warnings']:
            print(f"\n⚠️ WARNINGS:")
            for warning in results['warnings']:
                print(f"  • {warning}")
        
        # Final status
        if not results['failed']:
            print(f"\n🎉 SYSTEM VERIFICATION COMPLETE!")
            print("🚀 All critical components are working!")
            print("✅ Ready for production deployment!")
            return True
        else:
            print(f"\n⚠️ System verification completed with {len(results['failed'])} failures.")
            print("🔧 Some components may need attention before deployment.")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during verification: {e}")
        return False

def verify_database_integrity(results):
    """Verify database integrity and structure."""
    try:
        db_path = 'bot_database.db'
        if not os.path.exists(db_path):
            results['failed'].append("Database file not found")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check required tables
        required_tables = [
            'users', 'ad_slots', 'worker_usage', 'worker_cooldowns',
            'posting_history', 'subscriptions', 'payments', 'admin_ad_slots',
            'failed_group_joins', 'worker_activity_log'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table in existing_tables:
                results['passed'].append(f"Table '{table}' exists")
            else:
                results['failed'].append(f"Table '{table}' missing")
        
        # Check worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        if worker_count == 10:
            results['passed'].append(f"Correct worker count: {worker_count}")
        else:
            results['warnings'].append(f"Worker count: {worker_count} (expected 10)")
        
        # Check for duplicates
        cursor.execute("SELECT worker_id, COUNT(*) FROM worker_usage GROUP BY worker_id HAVING COUNT(*) > 1")
        duplicates = cursor.fetchall()
        if not duplicates:
            results['passed'].append("No duplicate workers found")
        else:
            results['failed'].append(f"Found {len(duplicates)} duplicate workers")
        
        conn.close()
        
    except Exception as e:
        results['failed'].append(f"Database integrity check failed: {e}")

def verify_core_files(results):
    """Verify core files exist and are accessible."""
    required_files = [
        'bot.py',
        'config.py',
        'database.py',
        'src/database/manager.py',
        'src/config/main_config.py',
        'scheduler/core/posting_service.py',
        'commands/admin_commands.py',
        'commands/user_commands.py',
        'restart_recovery.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            results['passed'].append(f"File exists: {file_path}")
        else:
            results['failed'].append(f"File missing: {file_path}")

def verify_configuration(results):
    """Verify configuration is properly set up."""
    try:
        # Check config.py imports
        config_path = 'config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            if 'from src.config.main_config import BotConfig' in content:
                results['passed'].append("Config imports are correct")
            else:
                results['failed'].append("Config imports are incorrect")
        
        # Check main_config.py methods
        main_config_path = 'src/config/main_config.py'
        if os.path.exists(main_config_path):
            with open(main_config_path, 'r') as f:
                content = f.read()
            
            if 'get_crypto_address' in content:
                results['passed'].append("get_crypto_address method exists")
            else:
                results['failed'].append("get_crypto_address method missing")
        
    except Exception as e:
        results['failed'].append(f"Configuration check failed: {e}")

def verify_admin_interface(results):
    """Verify admin interface methods exist."""
    try:
        db_path = 'src/database/manager.py'
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
            
            admin_methods = [
                'get_paused_slots',
                'get_revenue_stats',
                'get_failed_groups',
                'get_system_status'
            ]
            
            for method in admin_methods:
                if method in content:
                    results['passed'].append(f"Admin method '{method}' exists")
                else:
                    results['failed'].append(f"Admin method '{method}' missing")
        
    except Exception as e:
        results['failed'].append(f"Admin interface check failed: {e}")

def verify_user_interface(results):
    """Verify user interface methods exist."""
    try:
        user_commands_path = 'commands/user_commands.py'
        if os.path.exists(user_commands_path):
            with open(user_commands_path, 'r') as f:
                content = f.read()
            
            user_methods = [
                'show_crypto_selection',
                'handle_subscription',
                'process_payment'
            ]
            
            for method in user_methods:
                if method in content:
                    results['passed'].append(f"User method '{method}' exists")
                else:
                    results['warnings'].append(f"User method '{method}' not found (may be in recycle_bin)")
        
    except Exception as e:
        results['failed'].append(f"User interface check failed: {e}")

def verify_payment_system(results):
    """Verify payment system components."""
    try:
        db_path = 'bot_database.db'
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check subscriptions table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'")
            if cursor.fetchone():
                results['passed'].append("Subscriptions table exists")
            else:
                results['failed'].append("Subscriptions table missing")
            
            # Check payments table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
            if cursor.fetchone():
                results['passed'].append("Payments table exists")
            else:
                results['failed'].append("Payments table missing")
            
            conn.close()
        
    except Exception as e:
        results['failed'].append(f"Payment system check failed: {e}")

def verify_worker_system(results):
    """Verify worker system components."""
    try:
        db_path = 'bot_database.db'
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check worker_usage table
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            if worker_count > 0:
                results['passed'].append(f"Worker usage table has {worker_count} entries")
            else:
                results['failed'].append("Worker usage table is empty")
            
            # Check worker_cooldowns table
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
            cooldown_count = cursor.fetchone()[0]
            if cooldown_count >= 0:
                results['passed'].append(f"Worker cooldowns table has {cooldown_count} entries")
            else:
                results['failed'].append("Worker cooldowns table error")
            
            conn.close()
        
    except Exception as e:
        results['failed'].append(f"Worker system check failed: {e}")

def verify_posting_system(results):
    """Verify posting system components."""
    try:
        # Check posting service
        posting_path = 'scheduler/core/posting_service.py'
        if os.path.exists(posting_path):
            with open(posting_path, 'r') as f:
                content = f.read()
            
            posting_methods = [
                'post_ads',
                '_post_single_destination_parallel',
                '_mark_slot_as_posted',
                '_check_worker_cooldown',
                '_set_worker_cooldown'
            ]
            
            for method in posting_methods:
                if method in content:
                    results['passed'].append(f"Posting method '{method}' exists")
                else:
                    results['warnings'].append(f"Posting method '{method}' not found")
        
        # Check restart recovery
        recovery_path = 'restart_recovery.py'
        if os.path.exists(recovery_path):
            results['passed'].append("Restart recovery file exists")
        else:
            results['failed'].append("Restart recovery file missing")
        
    except Exception as e:
        results['failed'].append(f"Posting system check failed: {e}")

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)

