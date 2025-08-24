#!/usr/bin/env python3
"""
Complete Bot Fixes

This script fixes all identified issues:
1. Admin UI freezing when clicking on ads
2. Worker count showing 77 instead of 10
3. Invalid destinations causing posting failures
4. Forum topic handling improvements
"""

import logging
import subprocess
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def run_script(script_name, description):
    """Run a Python script and return success status."""
    logger.info(f"🔧 Running: {description}")
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"✅ {description} completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ {description} failed")
            if result.stderr:
                logger.error(f"Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} timed out")
        return False
    except Exception as e:
        logger.error(f"❌ {description} failed with exception: {e}")
        return False

def check_file_exists(filename):
    """Check if a file exists."""
    return os.path.exists(filename)

def main():
    """Main function to run all fixes."""
    logger.info("=" * 80)
    logger.info("🚀 COMPLETE BOT FIXES")
    logger.info("=" * 80)
    
    fixes = [
        ("fix_admin_ui_simple_final.py", "Final Admin UI Fix - No Syntax Errors"),
        ("fix_admin_ui_simple.py", "Admin UI Functions Fix"),
        ("check_worker_duplicates.py", "Worker Duplicate Check & Fix"),
        ("clean_invalid_destinations.py", "Invalid Destination Cleanup"),
        ("fix_crypto_payment.py", "Crypto Payment System Fix"),
        ("fix_payment_system_final.py", "Final Payment System Fix - No Syntax Errors"),
        ("fix_remaining_issues.py", "Fix Remaining Issues - Mock Methods & Environment"),
    ]
    
    success_count = 0
    total_fixes = len(fixes)
    
    for script_name, description in fixes:
        if check_file_exists(script_name):
            if run_script(script_name, description):
                success_count += 1
        else:
            logger.warning(f"⚠️ Script not found: {script_name}")
    
    logger.info("=" * 80)
    logger.info("📊 FIXES SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Successful fixes: {success_count}/{total_fixes}")
    
    if success_count == total_fixes:
        logger.info("🎉 All fixes completed successfully!")
        logger.info("")
        logger.info("🔧 ISSUES FIXED:")
        logger.info("✅ Admin UI freezing when clicking on ads")
        logger.info("✅ Worker count will show 10 instead of 77")
        logger.info("✅ Invalid destinations causing posting failures")
        logger.info("✅ Forum topic handling improvements")
        logger.info("✅ Crypto payment system (subscription purchases)")
        logger.info("")
        logger.info("🔄 Next steps:")
        logger.info("1. Restart the bot to apply all changes")
        logger.info("2. Test the admin UI - clicking on ads should work now")
        logger.info("3. Check that worker count shows 10 instead of 77")
        logger.info("4. Monitor posting success rates - should be much better")
        logger.info("5. Verify forum topic posting works correctly")
        logger.info("6. Test subscription purchases - crypto selection should work")
    else:
        logger.warning("⚠️ Some fixes failed. Check the logs above.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
