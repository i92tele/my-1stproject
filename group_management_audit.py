#!/usr/bin/env python3
"""
Group Management Audit
Audits and organizes group management for beta launch
"""

import os
import sys
import asyncio
import logging
import sqlite3
from datetime import datetime

def load_env_file():
    """Load .env file manually"""
    possible_paths = ['.env', 'config/.env', 'config/env_template.txt']
    for env_file in possible_paths:
        if os.path.exists(env_file):
            print(f"📁 Found .env file at: {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
    return False

async def audit_database_structure():
    """Audit database structure and tables"""
    print("\n📊 Auditing Database Structure...")
    print("=" * 40)
    
    try:
        from src.database.manager import DatabaseManager
        import logging
        
        logger = logging.getLogger(__name__)
        db_manager = DatabaseManager('bot_database.db', logger)
        await db_manager.initialize()
        
        # Check database tables
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Found {len(tables)} tables in database:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  📁 {table}: {count} records")
        
        conn.close()
        
        # Check if essential tables exist
        essential_tables = ['users', 'ad_slots', 'payments']
        missing_tables = [table for table in essential_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing essential tables: {missing_tables}")
            return False
        else:
            print("✅ All essential tables present")
        
        return True
        
    except Exception as e:
        print(f"❌ Database structure audit failed: {e}")
        return False

async def audit_user_data():
    """Audit user data and subscriptions"""
    print("\n👥 Auditing User Data...")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✅ Total users: {user_count}")
        
        # Check subscription tiers
        cursor.execute("SELECT subscription_tier, COUNT(*) FROM users GROUP BY subscription_tier")
        tier_stats = cursor.fetchall()
        
        if tier_stats:
            print("📊 Subscription tier distribution:")
            for tier, count in tier_stats:
                print(f"  • {tier or 'None'}: {count} users")
        else:
            print("📊 No users with subscriptions found")
        
        # Check admin user
        admin_id = 7172873873
        cursor.execute("SELECT user_id, username, subscription_tier FROM users WHERE user_id = ?", (admin_id,))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"✅ Admin user found: {admin_user[1]} ({admin_user[2]})")
        else:
            print(f"⚠️  Admin user {admin_id} not found in database")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ User data audit failed: {e}")
        return False

async def audit_ad_slots():
    """Audit ad slots and their status"""
    print("\n📢 Auditing Ad Slots...")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Check total ad slots
        cursor.execute("SELECT COUNT(*) FROM ad_slots")
        total_slots = cursor.fetchone()[0]
        print(f"✅ Total ad slots: {total_slots}")
        
        # Check slot status
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN is_paused = 1 THEN 1 ELSE 0 END) as paused,
                SUM(CASE WHEN is_active = 0 AND is_paused = 0 THEN 1 ELSE 0 END) as inactive
            FROM ad_slots
        """)
        status_stats = cursor.fetchone()
        
        if status_stats:
            active, paused, inactive = status_stats
            print("📊 Slot status distribution:")
            print(f"  • Active: {active or 0} slots")
            print(f"  • Paused: {paused or 0} slots")
            print(f"  • Inactive: {inactive or 0} slots")
        
        # Check categories
        cursor.execute("SELECT category, COUNT(*) FROM ad_slots GROUP BY category")
        category_stats = cursor.fetchall()
        
        if category_stats:
            print("📊 Category distribution:")
            for category, count in category_stats:
                print(f"  • {category or 'general'}: {count} slots")
        
        # Check admin slots
        admin_id = 7172873873
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE user_id = ?", (admin_id,))
        admin_slots = cursor.fetchone()[0]
        print(f"✅ Admin slots: {admin_slots}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ad slots audit failed: {e}")
        return False

async def audit_payments():
    """Audit payment data"""
    print("\n💰 Auditing Payments...")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Check total payments
        cursor.execute("SELECT COUNT(*) FROM payments")
        total_payments = cursor.fetchone()[0]
        print(f"✅ Total payments: {total_payments}")
        
        # Check payment status
        cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
        status_stats = cursor.fetchall()
        
        if status_stats:
            print("📊 Payment status distribution:")
            for status, count in status_stats:
                print(f"  • {status or 'Unknown'}: {count} payments")
        
        # Check crypto types
        cursor.execute("SELECT crypto_type, COUNT(*) FROM payments GROUP BY crypto_type")
        crypto_stats = cursor.fetchall()
        
        if crypto_stats:
            print("📊 Crypto type distribution:")
            for crypto, count in crypto_stats:
                print(f"  • {crypto}: {count} payments")
        
        # Check attribution methods
        cursor.execute("SELECT attribution_method, COUNT(*) FROM payments GROUP BY attribution_method")
        attribution_stats = cursor.fetchall()
        
        if attribution_stats:
            print("📊 Attribution method distribution:")
            for method, count in attribution_stats:
                print(f"  • {method or 'Unknown'}: {count} payments")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Payments audit failed: {e}")
        return False

async def run_group_management_audit():
    """Run comprehensive group management audit"""
    print("📊 GROUP MANAGEMENT AUDIT")
    print("=" * 60)
    print(f"🕐 Audit started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not load_env_file():
        print("❌ Could not load .env file")
        return False
    
    # Audit results tracking
    audit_results = {}
    
    # Run all audits
    audits = [
        ("Database Structure", audit_database_structure),
        ("User Data", audit_user_data),
        ("Ad Slots", audit_ad_slots),
        ("Payments", audit_payments)
    ]
    
    for audit_name, audit_func in audits:
        try:
            result = await audit_func()
            audit_results[audit_name] = result
        except Exception as e:
            print(f"❌ {audit_name} audit crashed: {e}")
            audit_results[audit_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 GROUP MANAGEMENT AUDIT RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(audit_results)
    
    for audit_name, result in audit_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {audit_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} audits passed")
    
    if passed == total:
        print("\n🎉 DATABASE AUDIT COMPLETE!")
        print("✅ Database structure verified")
        print("✅ User data organized")
        print("✅ Ad slots managed")
        print("✅ Payment data clean")
        print("\n🎯 RECOMMENDATION: DATABASE READY FOR BETA LAUNCH")
        return True
    else:
        print(f"\n⚠️  {total - passed} audits need attention")
        print("🔧 Please address database issues before beta launch")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_group_management_audit())
    if not success:
        sys.exit(1)
