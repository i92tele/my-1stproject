#!/usr/bin/env python3
"""
Run All Critical Fixes

This script runs all the critical fixes needed to restore bot functionality:
1. Fix worker count (ensure exactly 10 workers)
2. Fix admin functions (add missing functions)
3. Verify syntax error is fixed

Usage:
    python run_all_critical_fixes.py
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def run_worker_count_fix():
    """Run the worker count fix."""
    logger.info("🔧 Step 1: Fixing worker count...")
    try:
        from fix_worker_count import fix_worker_count
        success = fix_worker_count()
        if success:
            logger.info("✅ Worker count fix completed successfully!")
            return True
        else:
            logger.error("❌ Worker count fix failed!")
            return False
    except Exception as e:
        logger.error(f"❌ Error running worker count fix: {e}")
        return False

def run_admin_functions_fix():
    """Run the admin functions fix."""
    logger.info("🔧 Step 2: Fixing admin functions...")
    try:
        from fix_admin_functions_simple import fix_admin_commands
        success = fix_admin_commands()
        if success:
            logger.info("✅ Admin functions fix completed successfully!")
            return True
        else:
            logger.error("❌ Admin functions fix failed!")
            return False
    except Exception as e:
        logger.error(f"❌ Error running admin functions fix: {e}")
        return False

def verify_syntax_error_fixed():
    """Verify that the syntax error in posting_service.py is fixed."""
    logger.info("🔧 Step 3: Verifying syntax error fix...")
    try:
        posting_service_path = "scheduler/core/posting_service.py"
        with open(posting_service_path, 'r') as file:
            content = file.read()
        
        # Check for the problematic pattern
        if "logger.error(f\"Error setting worker cooldown: {e" in content:
            logger.error("❌ Syntax error still exists in posting_service.py!")
            return False
        
        # Check for stray characters using a different approach
        if "}")" in content:
            logger.error("❌ Stray characters still exist in posting_service.py!")
            return False
        
        logger.info("✅ Syntax error fix verified!")
        return True
    except Exception as e:
        logger.error(f"❌ Error verifying syntax fix: {e}")
        return False

def main():
    """Main function to run all critical fixes."""
    logger.info("=" * 80)
    logger.info("🚀 RUNNING ALL CRITICAL FIXES")
    logger.info("=" * 80)
    
    all_success = True
    
    # Step 1: Fix worker count
    if not run_worker_count_fix():
        all_success = False
    
    # Step 2: Fix admin functions
    if not run_admin_functions_fix():
        all_success = False
    
    # Step 3: Verify syntax error fix
    if not verify_syntax_error_fixed():
        all_success = False
    
    # Summary
    logger.info("=" * 80)
    logger.info("📊 CRITICAL FIXES SUMMARY")
    logger.info("=" * 80)
    
    if all_success:
        logger.info("✅ ALL CRITICAL FIXES COMPLETED SUCCESSFULLY!")
        logger.info("")
        logger.info("🎯 NEXT STEPS:")
        logger.info("1. Restart the bot: python start_bot.py")
        logger.info("2. Test admin interface functionality")
        logger.info("3. Test worker count (should be exactly 10)")
        logger.info("4. Test bot responsiveness")
        logger.info("5. Test posting functionality")
        logger.info("")
        logger.info("🔧 The bot should now be fully functional!")
    else:
        logger.error("❌ SOME CRITICAL FIXES FAILED!")
        logger.error("Please check the errors above and fix them manually.")
        logger.error("The bot may not function properly until all fixes are applied.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
