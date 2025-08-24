#!/usr/bin/env python3
"""
Run Verification

Simple script to run the verification.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the verification
from verify_fixes import main

if __name__ == "__main__":
    main()
