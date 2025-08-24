#!/usr/bin/env python3
"""
Comprehensive Bot Fixes

This script runs all the identified fixes for the bot issues.
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
                              capture_output=True, text=True, timeout=60)
        
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
    logger.info("🚀 COMPREHENSIVE BOT FIXES")
    logger.info("=" * 80)
    
    fixes = [
        ("check_worker_duplicates.py", "Worker Duplicate Check & Fix"),
        ("clean_invalid_destinations.py", "Invalid Destination Cleanup"),
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
        logger.info("🔄 Next steps:")
        logger.info("1. Restart the bot to apply changes")
        logger.info("2. Monitor the logs for improved performance")
        logger.info("3. Check that worker count shows 10 instead of 77")
        logger.info("4. Verify forum topic posting works correctly")
    else:
        logger.warning("⚠️ Some fixes failed. Check the logs above.")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
