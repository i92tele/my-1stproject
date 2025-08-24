#!/usr/bin/env python3
"""
Run Admin Functions Fix

This script executes the admin functions fix.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the fix
from fix_admin_functions_simple import fix_admin_commands

if __name__ == "__main__":
    print("🔧 Running admin functions fix...")
    success = fix_admin_commands()
    if success:
        print("✅ Admin functions fix completed successfully!")
    else:
        print("❌ Admin functions fix failed!")
    print("Please restart the bot after this fix.")
