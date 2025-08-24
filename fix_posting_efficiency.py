#!/usr/bin/env python3
"""
Fix Posting Efficiency

This script improves the posting efficiency by:
1. Increasing global join limits to more reasonable values
2. Adding better handling for rate-limited destinations
3. Implementing destination validation
4. Creating a maintenance function to identify problematic destinations

Usage:
    python fix_posting_efficiency.py
"""

import os
import sys
import re
import logging
import sqlite3
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# File paths
POSTING_SERVICE_PATH = "scheduler/core/posting_service.py"
DATABASE_PATH = "bot_database.db"

async def fix_global_join_limits():
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

async def add_rate_limit_handling():
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
        error_pattern = r'(\s+if "rate_limit" in error_message or "wait of" in error_message:.*?)(\s+return False)'
        error_replacement = r'\1\n            # Extract wait time from error message\n            wait_time = 3600  # Default 1 hour\n            match = re.search(r\'wait of (\\d+) seconds\', error_message)\n            if match:\n                wait_time = int(match.group(1))\n            \n            # Store destination with expiry time\n            destination_id = destination.get("destination_id", "")\n            self.rate_limited_destinations[destination_id] = time.time() + wait_time\n            logger.info(f"🕒 Rate limit for {destination_id}: {wait_time}s")\2'
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
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added improved rate limit handling")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add rate limit handling: {e}")
        return False

async def add_destination_validation():
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
        class_end_pattern = r'(\s+async def _check_worker_cooldown.*?(?:return|pass).*?\n)(\s*?)$'
        validate_method = r'\1\n    async def validate_destination(self, destination: Dict) -> bool:\n        """Check if a destination is valid before attempting to post."""\n        destination_id = destination.get("destination_id", "")\n        destination_name = destination.get("name", "")\n        \n        # Skip known invalid destinations\n        if destination_id in self.invalid_destinations:\n            logger.info(f"⏭️ Skipping known invalid destination: {destination_name} ({destination_id})")\n            return False\n            \n        # Skip rate-limited destinations\n        if destination_id in self.rate_limited_destinations:\n            if time.time() < self.rate_limited_destinations[destination_id]:\n                remaining = int(self.rate_limited_destinations[destination_id] - time.time())\n                logger.info(f"⏭️ Skipping rate-limited destination {destination_name} for {remaining}s")\n                return False\n        \n        # Check format validity (basic checks)\n        if "/" in destination_id and not destination_id.split("/")[0]:\n            logger.warning(f"❌ Invalid destination format: {destination_name} ({destination_id})")\n            self.invalid_destinations.add(destination_id)\n            return False\n        \n        # Check for known invalid patterns\n        invalid_patterns = ["@c/", "@social/", "@mafiamarketss/", "@crystalmarketss/"]\n        for pattern in invalid_patterns:\n            if pattern.lower() in destination_id.lower() or pattern.lower() in destination_name.lower():\n                logger.warning(f"❌ Invalid destination pattern {pattern}: {destination_name} ({destination_id})")\n                self.invalid_destinations.add(destination_id)\n                return False\n        \n        return True\n\2'
        content = re.sub(class_end_pattern, validate_method, content, flags=re.DOTALL)
        
        # Call validation before posting
        post_pattern = r'(\s+async def _post_single_destination_parallel\(self, ad_slot: Dict, destination: Dict, worker, results: Dict\[str, Any\], posted_slots: set = None\):.*?)(\s+# Skip rate-limited destinations)'
        post_replacement = r'\1\n        # Validate destination first\n        if not await self.validate_destination(destination):\n            results[destination.get("destination_id", "")] = {"success": False, "error": "Invalid destination"}\n            return False\2'
        content = re.sub(post_pattern, post_replacement, content, flags=re.DOTALL)
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added destination validation")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add destination validation: {e}")
        return False

async def add_destination_cleanup():
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
        cleanup_method = r'\1\n    async def clean_invalid_destinations(self):\n        """Remove destinations that consistently fail."""\n        logger.info("🧹 Running destination cleanup check...")\n        try:\n            # Get destinations with high failure rates\n            query = """\n            SELECT d.destination_id, d.name, \n                   COUNT(CASE WHEN ph.success = 0 THEN 1 END) as failures,\n                   COUNT(*) as total_attempts\n            FROM destinations d\n            LEFT JOIN posting_history ph ON d.destination_id = ph.destination_id\n            GROUP BY d.destination_id\n            HAVING failures > 5 AND (failures * 1.0 / total_attempts) > 0.8\n            """\n            \n            results = await self.db.execute_query(query)\n            \n            # Log problematic destinations and add to invalid set\n            for row in results:\n                dest_id = row["destination_id"]\n                logger.warning(f"🚫 Problematic destination: {row[\'name\']} ({dest_id}) - {row[\'failures\']}/{row[\'total_attempts\']} failures")\n                self.invalid_destinations.add(dest_id)\n            \n            if results:\n                logger.info(f"✅ Added {len(results)} problematic destinations to invalid list")\n            else:\n                logger.info("✅ No problematic destinations found")\n                \n        except Exception as e:\n            logger.error(f"❌ Error in destination cleanup: {e}")\n\2'
        content = re.sub(class_end_pattern, cleanup_method, content, flags=re.DOTALL)
        
        # Call cleanup in post_ads method
        post_ads_pattern = r'(\s+async def post_ads\(self.*?\):.*?)(\s+start_time = time\.time\(\))'
        post_ads_replacement = r'\1\n        # Periodically clean up invalid destinations\n        if random.random() < 0.1:  # 10% chance on each post_ads call\n            await self.clean_invalid_destinations()\2'
        content = re.sub(post_ads_pattern, post_ads_replacement, content, flags=re.DOTALL)
        
        with open(POSTING_SERVICE_PATH, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added destination cleanup functionality")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add destination cleanup: {e}")
        return False

async def create_cleanup_script():
    """Create a standalone script to manually clean up problematic destinations."""
    logger.info("🔧 Creating standalone cleanup script...")
    
    try:
        script_path = "cleanup_destinations.py"
        script_content = """#!/usr/bin/env python3
\"\"\"
Cleanup Destinations

This script identifies and optionally disables problematic destinations
that have a high failure rate.

Usage:
    python cleanup_destinations.py [--disable]

Options:
    --disable    Actually disable problematic destinations in the database
\"\"\"

import os
import sys
import sqlite3
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def cleanup_destinations(disable=False):
    """Identify and optionally disable problematic destinations."""
    logger.info("🔍 Analyzing destination performance...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if destinations table has is_active column
        cursor.execute("PRAGMA table_info(destinations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        has_active_column = "is_active" in columns
        if not has_active_column and disable:
            logger.info("Adding is_active column to destinations table...")
            cursor.execute("ALTER TABLE destinations ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.commit()
        
        # Get destinations with high failure rates
        query = """
        SELECT d.destination_id, d.name, 
               COUNT(CASE WHEN ph.success = 0 THEN 1 END) as failures,
               COUNT(*) as total_attempts,
               (COUNT(CASE WHEN ph.success = 0 THEN 1 END) * 100.0 / COUNT(*)) as failure_rate
        FROM destinations d
        LEFT JOIN posting_history ph ON d.destination_id = ph.destination_id
        GROUP BY d.destination_id
        HAVING failures > 5 AND (failures * 1.0 / total_attempts) > 0.8
        ORDER BY failure_rate DESC, total_attempts DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            logger.info("✅ No problematic destinations found")
            return
        
        # Display problematic destinations
        logger.info(f"Found {len(results)} problematic destinations:")
        print("\\n{:<40} {:<10} {:<10} {:<10}".format("Destination", "Failures", "Total", "Rate %"))
        print("-" * 70)
        
        for row in results:
            print("{:<40} {:<10} {:<10} {:<10.1f}".format(
                f"{row['name']} ({row['destination_id']})",
                row['failures'],
                row['total_attempts'],
                row['failure_rate']
            ))
        
        # Disable problematic destinations if requested
        if disable and has_active_column:
            destination_ids = [row['destination_id'] for row in results]
            placeholders = ', '.join(['?' for _ in destination_ids])
            
            cursor.execute(f"UPDATE destinations SET is_active = 0 WHERE destination_id IN ({placeholders})", destination_ids)
            conn.commit()
            
            logger.info(f"✅ Disabled {len(destination_ids)} problematic destinations")
        elif disable:
            logger.warning("⚠️ Could not disable destinations: is_active column not found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up destinations: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Cleanup problematic destinations")
    parser.add_argument("--disable", action="store_true", help="Disable problematic destinations")
    args = parser.parse_args()
    
    cleanup_destinations(args.disable)

if __name__ == "__main__":
    main()
"""
        
        with open(script_path, 'w') as file:
            file.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"✅ Created standalone cleanup script: {script_path}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to create cleanup script: {e}")
        return False

async def main():
    """Main function to run all fixes."""
    logger.info("=" * 60)
    logger.info("🚀 STARTING POSTING EFFICIENCY IMPROVEMENTS")
    logger.info("=" * 60)
    
    # Run all fixes
    fixes = [
        ("Global Join Limits", fix_global_join_limits()),
        ("Rate Limit Handling", add_rate_limit_handling()),
        ("Destination Validation", add_destination_validation()),
        ("Destination Cleanup", add_destination_cleanup()),
        ("Standalone Cleanup Script", create_cleanup_script()),
    ]
    
    results = []
    for name, coro in fixes:
        logger.info("-" * 60)
        logger.info(f"🔧 APPLYING FIX: {name}")
        logger.info("-" * 60)
        result = await coro
        results.append((name, result))
    
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
    asyncio.run(main())
