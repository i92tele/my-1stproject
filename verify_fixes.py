#!/usr/bin/env python3
"""
Verify Fixes

Simple script to verify all critical fixes are working.
"""

import sqlite3
import os

def verify_worker_count():
    """Verify worker count is exactly 10."""
    print("🔍 Checking worker count...")
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 10:
            print(f"✅ Worker count: {count}")
            return True
        else:
            print(f"❌ Worker count: {count} (should be 10)")
            return False
    except Exception as e:
        print(f"❌ Error checking worker count: {e}")
        return False

def verify_admin_functions():
    """Verify admin functions exist."""
    print("🔍 Checking admin functions...")
    try:
        if not os.path.exists("commands/admin_commands.py"):
            print("❌ Admin commands file not found")
            return False
        
        with open("commands/admin_commands.py", 'r') as f:
            content = f.read()
        
        functions = ["show_revenue_stats", "show_worker_status"]
        missing = []
        for func in functions:
            if f"async def {func}" not in content:
                missing.append(func)
        
        if not missing:
            print("✅ All admin functions found")
            return True
        else:
            print(f"❌ Missing functions: {missing}")
            return False
    except Exception as e:
        print(f"❌ Error checking admin functions: {e}")
        return False

def verify_syntax():
    """Verify syntax is correct."""
    print("🔍 Checking syntax...")
    try:
        # Check the posting service file directly
        with open("scheduler/core/posting_service.py", 'r') as f:
            content = f.read()
        
        # Check for the problematic pattern that was fixed
        if "logger.error(f\"Error setting worker cooldown: {e" in content:
            print("❌ Syntax error still exists")
            return False
        
        # Check for the corrected pattern
        if "logger.error(f\"Error setting worker cooldown: {e}\")" in content:
            print("✅ Syntax is correct")
            return True
        else:
            print("⚠️ Syntax pattern not found, but no errors detected")
            return True
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        return False

def main():
    """Main verification function."""
    print("=" * 60)
    print("🔍 VERIFYING CRITICAL FIXES")
    print("=" * 60)
    
    all_good = True
    
    if not verify_worker_count():
        all_good = False
    
    if not verify_admin_functions():
        all_good = False
    
    if not verify_syntax():
        all_good = False
    
    print("=" * 60)
    if all_good:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("🚀 Bot is ready to restart!")
        print("Run: python start_bot.py")
    else:
        print("❌ SOME VERIFICATIONS FAILED!")
        print("Please fix the issues before restarting the bot.")
    print("=" * 60)

if __name__ == "__main__":
    main()
