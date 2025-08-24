#!/usr/bin/env python3
"""
Add Destination Validation

This script adds a validation function to check destinations before attempting to post:
- Adds validate_destination method
- Adds invalid_destinations set to track permanently invalid destinations
- Calls validation before attempting to post

Usage:
    python add_destination_validation.py
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

def add_destination_validation():
    """
    Add a validation function to check destinations before attempting to post.
    
    Changes:
    - Add validate_destination method
    - Add invalid_destinations set to track permanently invalid destinations
    - Call validation before attempting to post
    """
    logger.info("🔧 Adding destination validation...")
    
    try:
        with open(POSTING_SERVICE_PATH, 'r') as file:
            content = file.read()
        
        # Add invalid_destinations set to __init__
        init_pattern = r'(\s+def __init__\(self, .*?\):.*?)(\s+self\.last_global_join = None)'
        init_replacement = r'\1\n        # Track invalid destinations\n        self.invalid_destinations = set()  # Set of known invalid destination_ids\2'
        content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)
        
        # Add validate_destination method
        class_end_pattern = r'(\s+async def _set_worker_cooldown.*?(?:return|pass).*?\n)(\s*?)$'
        validate_method = r'\1\n    async def validate_destination(self, destination: Dict) -> bool:\n        """Check if a destination is valid before attempting to post."""\n        destination_id = destination.get("destination_id", "")\n        destination_name = destination.get("name", "")\n        \n        # Skip known invalid destinations\n        if destination_id in self.invalid_destinations:\n            logger.info(f"⏭️ Skipping known invalid destination: {destination_name} ({destination_id})")\n            return False\n            \n        # Skip rate-limited destinations\n        if hasattr(self, "rate_limited_destinations") and destination_id in self.rate_limited_destinations:\n            if time.time() < self.rate_limited_destinations[destination_id]:\n                remaining = int(self.rate_limited_destinations[destination_id] - time.time())\n                logger.info(f"⏭️ Skipping rate-limited destination {destination_name} for {remaining}s")\n                return False\n        \n        # Check format validity (basic checks)\n        if "/" in destination_id and not destination_id.split("/")[0]:\n            logger.warning(f"❌ Invalid destination format: {destination_name} ({destination_id})")\n            self.invalid_destinations.add(destination_id)\n            return False\n        \n        # Check for known invalid patterns\n        invalid_patterns = ["@c/", "@social/", "@mafiamarketss/", "@crystalmarketss/"]\n        for pattern in invalid_patterns:\n            if pattern.lower() in destination_id.lower() or pattern.lower() in destination_name.lower():\n                logger.warning(f"❌ Invalid destination pattern {pattern}: {destination_name} ({destination_id})")\n                self.invalid_destinations.add(destination_id)\n                return False\n        \n        return True\n\2'
        content = re.sub(class_end_pattern, validate_method, content, flags=re.DOTALL)
        
        # Call validation before posting
        post_pattern = r'(\s+async def _post_single_destination_parallel\(self, ad_slot: Dict, destination: Dict, worker, results: Dict\[str, Any\], posted_slots: set = None\):.*?)(\s+try:)'
        post_replacement = r'\1\n        # Validate destination first\n        if not await self.validate_destination(destination):\n            destination_id = destination.get("destination_id", "")\n            results[destination_id] = {"success": False, "error": "Invalid destination"}\n            return False\2'
        content = re.sub(post_pattern, post_replacement, content, flags=re.DOTALL)
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added destination validation")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add destination validation: {e}")
        return False

if __name__ == "__main__":
    if add_destination_validation():
        print("✅ Successfully added destination validation")
    else:
        print("❌ Failed to add destination validation")
