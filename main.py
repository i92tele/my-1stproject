#!/usr/bin/env python3
"""
Main entry point for AutoFarming Bot
Uses the organized src/ structure
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the bot
from bot import main

if __name__ == "__main__":
    main()
