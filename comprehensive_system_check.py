#!/usr/bin/env python3
"""
Comprehensive System Check
Identify any major flaws before beta release
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def comprehensive_system_check():
    """Comprehensive system check to identify major flaws."""
    print("🔍 COMPREHENSIVE SYSTEM CHECK")
    print("=" * 60)
    
    issues_found = []
    warnings = []
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        print("\n📊 DATABASE INTEGRITY CHECK:")
        print("-" * 35)
        
        # Check database schema
        required_tables = [
            'users', 'ad_slots', 'admin_ad_slots', 'destinations', 
            'slot_destinations', 'workers', 'worker_cooldowns', 
            'worker_activity_log', 'payments', 'subscriptions'
        ]
        
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")
                issues_found.append(f"Missing table: {table}")
        
        # Check for orphaned data
        print(f"\n🔍 DATA INTEGRITY CHECK:")
        print("-" * 25)
        
        # Check for orphaned slot destinations
        cursor.execute("""
            SELECT COUNT(*) FROM slot_destinations sd
            LEFT JOIN ad_slots s ON sd.slot_id = s.id
            LEFT JOIN admin_ad_slots aas ON sd.slot_id = aas.id
            WHERE s.id IS NULL AND aas.id IS NULL
        """)
        orphaned_destinations = cursor.fetchone()[0]
        if orphaned_destinations > 0:
            print(f"⚠️ {orphaned_destinations} orphaned slot destinations found")
            warnings.append(f"{orphaned_destinations} orphaned slot destinations")
        else:
            print("✅ No orphaned slot destinations")
        
        # Check for users without subscriptions
        cursor.execute("""
            SELECT COUNT(*) FROM users u
            LEFT JOIN subscriptions s ON u.user_id = s.user_id
            WHERE s.user_id IS NULL
        """)
        users_without_subs = cursor.fetchone()[0]
        if users_without_subs > 0:
            print(f"⚠️ {users_without_subs} users without subscriptions")
            warnings.append(f"{users_without_subs} users without subscriptions")
        else:
            print("✅ All users have subscription records")
        
        # Check for expired subscriptions that should be deactivated
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE subscription_expires < datetime('now') AND subscription_tier IS NOT NULL
        """)
        expired_active = cursor.fetchone()[0]
        if expired_active > 0:
            print(f"❌ {expired_active} expired but active subscriptions")
            issues_found.append(f"{expired_active} expired but active subscriptions")
        else:
            print("✅ No expired active subscriptions")
        
        print(f"\n📊 SCHEDULER HEALTH CHECK:")
        print("-" * 30)
        
        # Check active ad slots
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        active_user_slots = cursor.fetchone()[0]
        print(f"Active user slots: {active_user_slots}")
        
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
        active_admin_slots = cursor.fetchone()[0]
        print(f"Active admin slots: {active_admin_slots}")
        
        # Check destinations
        cursor.execute("SELECT COUNT(*) FROM destinations WHERE is_active = 1")
        active_destinations = cursor.fetchone()[0]
        print(f"Active destinations: {active_destinations}")
        
        if active_destinations == 0:
            print("❌ No active destinations - posting will fail")
            issues_found.append("No active destinations")
        
        # Check workers
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        print(f"Active workers: {active_workers}")
        
        if active_workers == 0:
            print("❌ No active workers - posting will fail")
            issues_found.append("No active workers")
        
        print(f"\n🔧 CONFIGURATION CHECK:")
        print("-" * 25)
        
        # Check critical environment variables
        critical_vars = [
            'BOT_TOKEN', 'ADMIN_ID', 'DATABASE_URL'
        ]
        
        for var in critical_vars:
            if hasattr(config, var.lower()) and getattr(config, var.lower()):
                print(f"✅ {var} is set")
            else:
                print(f"❌ {var} is missing")
                issues_found.append(f"Missing {var}")
        
        # Check payment addresses
        payment_vars = [
            'BTC_ADDRESS', 'ETH_ADDRESS', 'LTC_ADDRESS', 'SOL_ADDRESS', 'TON_ADDRESS'
        ]
        
        payment_issues = 0
        for var in payment_vars:
            if hasattr(config, var.lower()) and getattr(config, var.lower()):
                print(f"✅ {var} is set")
            else:
                print(f"⚠️ {var} is missing")
                payment_issues += 1
        
        if payment_issues > 0:
            warnings.append(f"{payment_issues} payment addresses missing")
        
        print(f"\n📈 PERFORMANCE CHECK:")
        print("-" * 25)
        
        # Check recent posting activity
        cursor.execute("""
            SELECT COUNT(*) FROM worker_activity_log 
            WHERE created_at > datetime('now', '-24 hours')
        """)
        recent_activity = cursor.fetchone()[0]
        print(f"Recent posting activity (24h): {recent_activity}")
        
        # Check success rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM worker_activity_log 
            WHERE created_at > datetime('now', '-24 hours')
        """)
        result = cursor.fetchone()
        if result and result[0] > 0:
            success_rate = (result[1] / result[0]) * 100
            print(f"Success rate (24h): {success_rate:.1f}%")
            
            if success_rate < 50:
                print("⚠️ Low success rate detected")
                warnings.append(f"Low success rate: {success_rate:.1f}%")
        else:
            print("No recent posting activity")
        
        print(f"\n🔒 SECURITY CHECK:")
        print("-" * 20)
        
        # Check admin access
        if hasattr(config, 'admin_id') and config.admin_id:
            print(f"✅ Admin ID configured: {config.admin_id}")
        else:
            print("❌ Admin ID not configured")
            issues_found.append("Admin ID not configured")
        
        # Check for any obvious security issues
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (config.admin_id,))
        admin_exists = cursor.fetchone()[0]
        if admin_exists:
            print("✅ Admin user exists in database")
        else:
            print("⚠️ Admin user not found in database")
            warnings.append("Admin user not in database")
        
        conn.close()
        
        print(f"\n📋 SUMMARY:")
        print("=" * 50)
        
        if issues_found:
            print(f"❌ CRITICAL ISSUES FOUND ({len(issues_found)}):")
            for issue in issues_found:
                print(f"  • {issue}")
        else:
            print("✅ No critical issues found")
        
        if warnings:
            print(f"\n⚠️ WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  • {warning}")
        else:
            print("✅ No warnings")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        print("=" * 25)
        
        if issues_found:
            print("❌ DO NOT RELEASE BETA - Fix critical issues first")
            print("   Address all critical issues before broadcasting")
        elif warnings:
            print("⚠️ REVIEW WARNINGS - Consider addressing before release")
            print("   System may work but could be improved")
        else:
            print("✅ SYSTEM READY - Safe to proceed with beta release")
            print("   All critical systems are functioning properly")
        
        return len(issues_found) == 0
        
    except Exception as e:
        print(f"❌ Error during system check: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_critical_functions():
    """Test critical functions to ensure they work properly."""
    print(f"\n🧪 CRITICAL FUNCTION TESTS:")
    print("=" * 40)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Test get_active_ads_to_send
        try:
            active_ads = await db.get_active_ads_to_send()
            print(f"✅ get_active_ads_to_send() works - {len(active_ads)} ads")
        except Exception as e:
            print(f"❌ get_active_ads_to_send() failed: {e}")
        
        # Test get_all_users
        try:
            users = await db.get_all_users()
            print(f"✅ get_all_users() works - {len(users)} users")
        except Exception as e:
            print(f"❌ get_all_users() failed: {e}")
        
        # Test get_stats
        try:
            stats = await db.get_stats()
            print(f"✅ get_stats() works - {stats['total_users']} users")
        except Exception as e:
            print(f"❌ get_stats() failed: {e}")
        
        print("✅ Critical function tests completed")
        
    except Exception as e:
        print(f"❌ Error testing critical functions: {e}")

async def main():
    """Main function."""
    print("🔍 PRE-BETA RELEASE SYSTEM CHECK")
    print("=" * 60)
    
    # Run comprehensive system check
    system_ok = await comprehensive_system_check()
    
    # Test critical functions
    await test_critical_functions()
    
    print(f"\n🎉 SYSTEM CHECK COMPLETE!")
    
    if system_ok:
        print("✅ SYSTEM IS READY FOR BETA RELEASE")
        print("   No critical issues found")
    else:
        print("❌ SYSTEM NOT READY FOR BETA RELEASE")
        print("   Critical issues must be fixed first")
    
    print(f"\n📋 NEXT STEPS:")
    if system_ok:
        print("1. ✅ System check passed")
        print("2. 🧪 Test broadcast function")
        print("3. 📢 Send beta release announcement")
    else:
        print("1. ❌ Fix critical issues identified above")
        print("2. 🔍 Re-run system check")
        print("3. 📢 Only broadcast after issues are resolved")

if __name__ == "__main__":
    asyncio.run(main())
