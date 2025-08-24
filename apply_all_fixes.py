#!/usr/bin/env python3
"""
Apply All Posting Efficiency Fixes

This script applies all the posting efficiency fixes:
1. Increase global join limits
2. Add rate limit handling
3. Add destination validation
4. Add destination cleanup

Usage:
    python apply_all_fixes.py
"""

import logging
import importlib.util
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def import_module_from_file(module_name, file_path):
    """Import a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def apply_all_fixes():
    """Apply all posting efficiency fixes."""
    logger.info("=" * 60)
    logger.info("🚀 STARTING POSTING EFFICIENCY IMPROVEMENTS")
    logger.info("=" * 60)
    
    # Make all scripts executable
    try:
        for script in ["fix_global_join_limits.py", "add_rate_limit_handling.py", 
                      "add_destination_validation.py", "add_destination_cleanup.py", 
                      "cleanup_destinations.py"]:
            if os.path.exists(script):
                os.chmod(script, 0o755)
                logger.info(f"✅ Made {script} executable")
    except Exception as e:
        logger.error(f"❌ Error making scripts executable: {e}")
    
    # List of fixes to apply
    fixes = [
        ("Global Join Limits", "fix_global_join_limits.py", "fix_global_join_limits"),
        ("Rate Limit Handling", "add_rate_limit_handling.py", "add_rate_limit_handling"),
        ("Destination Validation", "add_destination_validation.py", "add_destination_validation"),
        ("Destination Cleanup", "add_destination_cleanup.py", "add_destination_cleanup")
    ]
    
    results = []
    for name, script_file, function_name in fixes:
        logger.info("-" * 60)
        logger.info(f"🔧 APPLYING FIX: {name}")
        logger.info("-" * 60)
        
        try:
            # Import the module
            if os.path.exists(script_file):
                module = import_module_from_file(function_name, script_file)
                # Get the main function
                fix_function = getattr(module, function_name)
                # Apply the fix
                result = fix_function()
                results.append((name, result))
            else:
                logger.error(f"❌ Fix script not found: {script_file}")
                results.append((name, False))
        except Exception as e:
            logger.error(f"❌ Error applying fix {name}: {e}")
            results.append((name, False))
    
    # Make apply_all_fixes.py executable
    try:
        os.chmod("apply_all_fixes.py", 0o755)
        logger.info("✅ Made apply_all_fixes.py executable")
    except Exception as e:
        logger.error(f"❌ Error making apply_all_fixes.py executable: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 SUMMARY OF APPLIED FIXES")
    logger.info("=" * 60)
    
    all_successful = True
    for name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        if not result:
            all_successful = False
        logger.info(f"{status}: {name}")
    
    if all_successful:
        logger.info("=" * 60)
        logger.info("🎉 ALL FIXES SUCCESSFULLY APPLIED!")
        logger.info("=" * 60)
        logger.info("The posting system should now be more efficient with:")
        logger.info("1. More reasonable global join limits (50/day, 20/hour)")
        logger.info("2. Better handling of rate-limited destinations")
        logger.info("3. Validation to skip known invalid destinations")
        logger.info("4. Automatic cleanup of problematic destinations")
        logger.info("")
        logger.info("You can also manually clean up destinations with:")
        logger.info("python cleanup_destinations.py --disable")
    else:
        logger.error("=" * 60)
        logger.error("⚠️ SOME FIXES FAILED TO APPLY")
        logger.error("=" * 60)
        logger.error("Please check the logs above for details.")

if __name__ == "__main__":
    apply_all_fixes()
