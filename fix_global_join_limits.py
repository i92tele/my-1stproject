#!/usr/bin/env python3
"""
Fix Global Join Limits

This script increases the global join limits to more reasonable values:
- Daily limit: 10 → 50 (5 per worker with 10 workers)
- Hourly limit: 2 → 20 (2 per worker with 10 workers)

Usage:
    python fix_global_join_limits.py
"""

import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# File paths
POSTING_SERVICE_PATH = "scheduler/core/posting_service.py"

def fix_global_join_limits():
    """
    Increase the global join limits to more reasonable values.
    
    Changes:
    - Daily limit: 10 → 50 (5 per worker with 10 workers)
    - Hourly limit: 2 → 20 (2 per worker with 10 workers)
    """
    logger.info("🔧 Fixing global join limits...")
    
    try:
        with open(POSTING_SERVICE_PATH, 'r') as file:
            content = file.read()
        
        # Replace daily limit
        content = re.sub(
            r'(\s+# Check daily limit \(10 joins per day across all workers\)\s+if self\.global_join_count_today >= )10:',
            r'\g<1>50:  # Increased from 10 to 50 (5 per worker)',
            content
        )
        
        # Replace hourly limit
        content = re.sub(
            r'(\s+# Check hourly limit \(2 joins per hour across all workers\)\s+.*\s+.*\s+if self\.global_join_count_today >= )2:',
            r'\g<1>20:  # Increased from 2 to 20 (2 per worker)',
            content
        )
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Global join limits increased: daily=50, hourly=20")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to fix global join limits: {e}")
        return False

if __name__ == "__main__":
    if fix_global_join_limits():
        print("✅ Successfully increased global join limits")
    else:
        print("❌ Failed to increase global join limits")
