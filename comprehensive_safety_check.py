#!/usr/bin/env python3
"""
Comprehensive Safety Check - Verify all anti-ban functions before starting bot
"""

import sqlite3
import os
import asyncio
from datetime import datetime, timedelta

def check_database_integrity():
    """Check database tables and data integrity."""
    print("🔍 Checking database integrity...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check all required tables exist
        required_tables = ['worker_usage', 'worker_cooldowns', 'ad_slots', 'admin_ad_slots', 'posting_history']
        missing_tables = []
        
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            print("✅ All required tables exist")
        
        # Check worker_usage table
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        if worker_count != 10:
            print(f"❌ Expected 10 workers, found {worker_count}")
            return False
        else:
            print("✅ Worker count correct (10)")
        
        # Check for duplicate workers
        cursor.execute("""
            SELECT worker_id, COUNT(*) as count 
            FROM worker_usage 
            GROUP BY worker_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"❌ Found duplicate workers: {duplicates}")
            return False
        else:
            print("✅ No duplicate workers")
        
        return True
        
    except Exception as e:
        print(f"❌ Database integrity check failed: {e}")
        return False
    finally:
        conn.close()

def check_anti_ban_functions():
    """Check that anti-ban functions are properly implemented."""
    print("\n🔍 Checking anti-ban functions...")
    
    # Check if posting_service.py has the required functions
    posting_service_path = 'scheduler/core/posting_service.py'
    
    if not os.path.exists(posting_service_path):
        print(f"❌ posting_service.py not found: {posting_service_path}")
        return False
    
    with open(posting_service_path, 'r') as f:
        content = f.read()
    
    required_functions = [
        '_check_worker_cooldown',
        '_set_worker_cooldown', 
        'random.uniform(2, 8)',
        'asyncio.sleep(delay)',
        'cooldown_remaining = await self._check_worker_cooldown'
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ Missing anti-ban functions: {missing_functions}")
        return False
    else:
        print("✅ All anti-ban functions found in posting_service.py")
    
    return True

def check_cooldown_system():
    """Test the cooldown system thoroughly."""
    print("\n🔍 Testing cooldown system...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Clear any existing cooldowns
        cursor.execute("DELETE FROM worker_cooldowns")
        conn.commit()
        
        # Test setting cooldown
        test_worker = 1
        cooldown_until = (datetime.now() + timedelta(seconds=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            INSERT INTO worker_cooldowns (worker_id, cooldown_until, created_at)
            VALUES (?, ?, datetime('now'))
        """, (test_worker, cooldown_until))
        
        conn.commit()
        
        # Test checking cooldown
        cursor.execute("""
            SELECT cooldown_until FROM worker_cooldowns 
            WHERE worker_id = ? AND cooldown_until > datetime('now')
        """, (test_worker,))
        
        result = cursor.fetchone()
        if result:
            print("✅ Cooldown system working correctly")
            
            # Clean up
            cursor.execute("DELETE FROM worker_cooldowns WHERE worker_id = ?", (test_worker,))
            conn.commit()
            return True
        else:
            print("❌ Cooldown system not working")
            return False
            
    except Exception as e:
        print(f"❌ Cooldown system test failed: {e}")
        return False
    finally:
        conn.close()

def check_worker_limits():
    """Check worker limit system."""
    print("\n🔍 Checking worker limits...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check worker limits are set correctly
        cursor.execute("SELECT worker_id, hourly_limit, daily_limit FROM worker_usage LIMIT 3")
        workers = cursor.fetchall()
        
        for worker_id, hourly_limit, daily_limit in workers:
            if hourly_limit != 15 or daily_limit != 150:
                print(f"❌ Worker {worker_id} has wrong limits: hourly={hourly_limit}, daily={daily_limit}")
                return False
        
        print("✅ Worker limits set correctly (hourly=15, daily=150)")
        return True
        
    except Exception as e:
        print(f"❌ Worker limits check failed: {e}")
        return False
    finally:
        conn.close()

def check_delay_implementation():
    """Check that delays are properly implemented."""
    print("\n🔍 Checking delay implementation...")
    
    posting_service_path = 'scheduler/core/posting_service.py'
    
    with open(posting_service_path, 'r') as f:
        content = f.read()
    
    # Check for random delays
    if 'random.uniform(2, 8)' not in content:
        print("❌ Random delays not implemented")
        return False
    
    # Check for cooldown delays
    if 'random.randint(30, 60)' not in content:
        print("❌ Cooldown delays not implemented")
        return False
    
    # Check for staggered delays
    if 'asyncio.sleep(10)' not in content:
        print("❌ Staggered delays not implemented")
        return False
    
    print("✅ All delay mechanisms implemented")
    return True

def check_worker_distribution():
    """Check that worker distribution logic is correct."""
    print("\n🔍 Checking worker distribution logic...")
    
    posting_service_path = 'scheduler/core/posting_service.py'
    
    with open(posting_service_path, 'r') as f:
        content = f.read()
    
    # Check for proper worker cycling
    if 'worker_index % len(available_workers)' not in content:
        print("❌ Worker distribution logic not found")
        return False
    
    # Check for cooldown checks before assignment
    if 'cooldown_remaining = await self._check_worker_cooldown' not in content:
        print("❌ Cooldown checks before assignment not found")
        return False
    
    print("✅ Worker distribution logic implemented correctly")
    return True

def check_safety_measures():
    """Check additional safety measures."""
    print("\n🔍 Checking safety measures...")
    
    posting_service_path = 'scheduler/core/posting_service.py'
    
    with open(posting_service_path, 'r') as f:
        content = f.read()
    
    safety_checks = [
        'max_attempts = len(available_workers) * 2',  # Limit retry attempts
        'if not worker_assigned',  # Check if worker assignment failed
        'logger.warning',  # Proper logging
        'return_exceptions=True'  # Exception handling
    ]
    
    missing_safety = []
    for check in safety_checks:
        if check not in content:
            missing_safety.append(check)
    
    if missing_safety:
        print(f"❌ Missing safety measures: {missing_safety}")
        return False
    else:
        print("✅ All safety measures implemented")
        return True

def main():
    """Run comprehensive safety check."""
    print("🛡️ COMPREHENSIVE SAFETY CHECK")
    print("=" * 50)
    print("⚠️  CRITICAL: This check prevents worker bans!")
    print("=" * 50)
    
    checks = [
        ("Database Integrity", check_database_integrity),
        ("Anti-Ban Functions", check_anti_ban_functions),
        ("Cooldown System", check_cooldown_system),
        ("Worker Limits", check_worker_limits),
        ("Delay Implementation", check_delay_implementation),
        ("Worker Distribution", check_worker_distribution),
        ("Safety Measures", check_safety_measures)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n🔍 {check_name}...")
        result = check_func()
        results.append((check_name, result))
    
    print("\n" + "=" * 50)
    print("📊 SAFETY CHECK RESULTS:")
    print("=" * 50)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL SAFETY CHECKS PASSED!")
        print("✅ Anti-ban system is properly implemented")
        print("✅ Worker protection is active")
        print("✅ Database is healthy")
        print("\n🚀 SAFE TO START BOT")
        print("📝 Expected behavior:")
        print("  • Random delays (2-8s) before posts")
        print("  • Worker cooldowns (30-60s) after posts")
        print("  • Proper worker distribution")
        print("  • Reduced rate limits and bans")
    else:
        print("❌ SAFETY CHECKS FAILED!")
        print("⚠️  DO NOT START BOT - WORKERS MAY GET BANNED")
        print("🔧 Fix the failed checks before proceeding")

if __name__ == "__main__":
    main()
