#!/usr/bin/env python3
"""
Run Worker Count Fix

This script executes the worker count fix.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the fix
from fix_worker_count import fix_worker_count

if __name__ == "__main__":
    print("🔧 Running worker count fix...")
    success = fix_worker_count()
    if success:
        print("✅ Worker count fix completed successfully!")
    else:
        print("❌ Worker count fix failed!")
    print("Please restart the bot after this fix.")
