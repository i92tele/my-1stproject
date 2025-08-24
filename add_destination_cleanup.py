#!/usr/bin/env python3
"""
Add Destination Cleanup

This script adds a maintenance function to identify problematic destinations:
- Adds clean_invalid_destinations method
- Calls this method periodically to identify and mark problematic destinations

Usage:
    python add_destination_cleanup.py
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

def add_destination_cleanup():
    """
    Add a maintenance function to identify problematic destinations.
    
    Changes:
    - Add clean_invalid_destinations method
    - Call this method periodically to identify and mark problematic destinations
    """
    logger.info("🔧 Adding destination cleanup functionality...")
    
    try:
        with open(POSTING_SERVICE_PATH, 'r') as file:
            content = file.read()
        
        # Add clean_invalid_destinations method
        class_end_pattern = r'(\s+async def validate_destination.*?return True\s*\n)(\s*?)$'
        cleanup_method = r'\1\n    async def clean_invalid_destinations(self):\n        """Remove destinations that consistently fail."""\n        logger.info("🧹 Running destination cleanup check...")\n        try:\n            # Get destinations with high failure rates\n            query = """\n            SELECT d.destination_id, d.name, \n                   COUNT(CASE WHEN ph.success = 0 THEN 1 END) as failures,\n                   COUNT(*) as total_attempts\n            FROM destinations d\n            LEFT JOIN posting_history ph ON d.destination_id = ph.destination_id\n            GROUP BY d.destination_id\n            HAVING failures > 5 AND (failures * 1.0 / total_attempts) > 0.8\n            """\n            \n            results = await self.database.execute_query(query)\n            \n            # Log problematic destinations and add to invalid set\n            for row in results:\n                dest_id = row["destination_id"]\n                logger.warning(f"🚫 Problematic destination: {row[\'name\']} ({dest_id}) - {row[\'failures\']}/{row[\'total_attempts\']} failures")\n                self.invalid_destinations.add(dest_id)\n            \n            if results:\n                logger.info(f"✅ Added {len(results)} problematic destinations to invalid list")\n            else:\n                logger.info("✅ No problematic destinations found")\n                \n        except Exception as e:\n            logger.error(f"❌ Error in destination cleanup: {e}")\n\2'
        content = re.sub(class_end_pattern, cleanup_method, content, flags=re.DOTALL)
        
        # Call cleanup in post_ads method
        post_ads_pattern = r'(\s+async def post_ads\(self.*?\):.*?)(\s+# Perform restart recovery on first run)'
        post_ads_replacement = r'\1\n        # Periodically clean up invalid destinations\n        if random.random() < 0.1:  # 10% chance on each post_ads call\n            await self.clean_invalid_destinations()\n\2'
        content = re.sub(post_ads_pattern, post_ads_replacement, content, flags=re.DOTALL)
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added destination cleanup functionality")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add destination cleanup: {e}")
        return False

if __name__ == "__main__":
    if add_destination_cleanup():
        print("✅ Successfully added destination cleanup functionality")
    else:
        print("❌ Failed to add destination cleanup functionality")
