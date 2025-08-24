#!/usr/bin/env python3
"""
Add Rate Limit Handling

This script adds better handling for rate-limited destinations:
- Adds a dictionary to track rate-limited destinations with expiry times
- Extracts wait time from error messages
- Skips posting to rate-limited destinations until the wait time expires

Usage:
    python add_rate_limit_handling.py
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

def add_rate_limit_handling():
    """
    Add better handling for rate-limited destinations.
    
    Changes:
    - Add a dictionary to track rate-limited destinations
    - Extract wait time from error messages
    - Skip posting to rate-limited destinations until the wait time expires
    """
    logger.info("🔧 Adding improved rate limit handling...")
    
    try:
        with open(POSTING_SERVICE_PATH, 'r') as file:
            content = file.read()
        
        # Add rate_limited_destinations dictionary to __init__
        init_pattern = r'(\s+def __init__\(self, .*?\):.*?)(\s+self\.last_global_join = None)'
        init_replacement = r'\1\n        # Track rate-limited destinations with expiry times\n        self.rate_limited_destinations = {}  # {destination_id: expiry_timestamp}\2'
        content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)
        
        # Add rate limit detection in error handling
        error_pattern = r'(\s+if "rate_limit" in error_message or "wait of" in error_message:.*?)(\s+ban_detected = True\s+ban_type = "rate_limit")'
        error_replacement = r'\1\n                    # Extract wait time from error message\n                    wait_time = 3600  # Default 1 hour\n                    match = re.search(r\'wait of (\\d+) seconds\', error_message)\n                    if match:\n                        wait_time = int(match.group(1))\n                    \n                    # Store destination with expiry time\n                    destination_id = destination.get("destination_id", "")\n                    self.rate_limited_destinations[destination_id] = time.time() + wait_time\n                    logger.info(f"🕒 Rate limit for {destination_id}: {wait_time}s")\2'
        content = re.sub(error_pattern, error_replacement, content, flags=re.DOTALL)
        
        # Add import for time module if not present
        if 'import time' not in content:
            content = re.sub(
                r'(import .*?\n\n)',
                r'\1import time\n',
                content,
                count=1
            )
        
        # Add check before posting to skip rate-limited destinations
        post_pattern = r'(\s+async def _post_single_destination_parallel\(self, ad_slot: Dict, destination: Dict, worker, results: Dict\[str, Any\], posted_slots: set = None\):.*?)(\s+try:)'
        post_replacement = r'\1\n        # Skip rate-limited destinations\n        destination_id = destination.get("destination_id", "")\n        if destination_id in self.rate_limited_destinations:\n            if time.time() < self.rate_limited_destinations[destination_id]:\n                remaining = int(self.rate_limited_destinations[destination_id] - time.time())\n                logger.info(f"⏭️ Skipping rate-limited destination {destination_id} for {remaining}s")\n                results[destination_id] = {"success": False, "error": f"Rate limited for {remaining}s"}\n                return False\n            else:\n                # Expired, remove from tracking\n                del self.rate_limited_destinations[destination_id]\2'
        content = re.sub(post_pattern, post_replacement, content, flags=re.DOTALL)
        
        # Add import for re module if not present
        if 'import re' not in content:
            content = re.sub(
                r'(import .*?\n\n)',
                r'\1import re\n',
                content,
                count=1
            )
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added improved rate limit handling")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add rate limit handling: {e}")
        return False

if __name__ == "__main__":
    if add_rate_limit_handling():
        print("✅ Successfully added rate limit handling")
    else:
        print("❌ Failed to add rate limit handling")
