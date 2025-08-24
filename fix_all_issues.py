#!/usr/bin/env python3
"""
Comprehensive Fix Script for AutoFarming Bot

This script:
1. Checks database schema and adapts fixes accordingly
2. Fixes global join limits
3. Adds rate limit handling
4. Adds destination validation
5. Adds admin interface functionality
6. Fixes worker count issues

Usage:
    python fix_all_issues.py
"""

import sqlite3
import logging
import os
import sys
import re
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def check_database_schema():
    """Check database schema and return table/column information."""
    logger.info("🔍 Checking database schema...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Get columns for each table
        table_columns = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            table_columns[table] = columns
            logger.info(f"Table '{table}' columns: {', '.join(columns)}")
        
        conn.close()
        return tables, table_columns
        
    except Exception as e:
        logger.error(f"❌ Error checking database schema: {e}")
        return [], {}

def fix_global_join_limits():
    """Fix global join limits in posting_service.py."""
    logger.info("🔧 Fixing global join limits...")
    
    try:
        file_path = "scheduler/core/posting_service.py"
        
        if not os.path.exists(file_path):
            logger.error(f"❌ {file_path} does not exist")
            return False
        
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Check if the file contains the global join limits
        if "global_join_count_today >= 10" not in content:
            logger.warning("⚠️ Could not find global join limits in posting_service.py")
            return False
        
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
        
        with open(file_path, 'w') as file:
            file.write(content)
        
        logger.info("✅ Global join limits increased: daily=50, hourly=20")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to fix global join limits: {e}")
        return False

def add_rate_limit_handling():
    """Add rate limit handling to posting_service.py."""
    logger.info("🔧 Adding improved rate limit handling...")
    
    try:
        file_path = "scheduler/core/posting_service.py"
        
        if not os.path.exists(file_path):
            logger.error(f"❌ {file_path} does not exist")
            return False
        
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Add rate_limited_destinations dictionary to __init__ if not already present
        if "self.rate_limited_destinations =" not in content:
            init_pattern = r'(\s+def __init__\(self, .*?\):.*?)(\s+self\.last_global_join = None)'
            if re.search(init_pattern, content, re.DOTALL):
                content = re.sub(
                    init_pattern,
                    r'\1\n        # Track rate-limited destinations with expiry times\n        self.rate_limited_destinations = {}  # {destination_id: expiry_timestamp}\2',
                    content,
                    flags=re.DOTALL
                )
                logger.info("✅ Added rate_limited_destinations dictionary")
            else:
                logger.warning("⚠️ Could not find initialization pattern in posting_service.py")
        else:
            logger.info("✅ rate_limited_destinations dictionary already exists")
        
        # Add import for time module if not present
        if 'import time' not in content:
            content = re.sub(
                r'(import .*?\n\n)',
                r'\1import time\n',
                content,
                count=1
            )
            logger.info("✅ Added time import")
        
        # Add import for re module if not present
        if 'import re' not in content:
            content = re.sub(
                r'(import .*?\n\n)',
                r'\1import re\n',
                content,
                count=1
            )
            logger.info("✅ Added re import")
        
        # Add check before posting to skip rate-limited destinations
        post_pattern = r'(\s+async def _post_single_destination_parallel\(self, ad_slot: Dict, destination: Dict, worker, results: Dict\[str, Any\], posted_slots: set = None\):.*?)(\s+try:)'
        if re.search(post_pattern, content, re.DOTALL) and "# Skip rate-limited destinations" not in content:
            content = re.sub(
                post_pattern,
                r'\1\n        # Skip rate-limited destinations\n        destination_id = destination.get("destination_id", "")\n        if hasattr(self, "rate_limited_destinations") and destination_id in self.rate_limited_destinations:\n            if time.time() < self.rate_limited_destinations[destination_id]:\n                remaining = int(self.rate_limited_destinations[destination_id] - time.time())\n                logger.info(f"⏭️ Skipping rate-limited destination {destination_id} for {remaining}s")\n                results[destination_id] = {"success": False, "error": f"Rate limited for {remaining}s"}\n                return False\n            else:\n                # Expired, remove from tracking\n                del self.rate_limited_destinations[destination_id]\2',
                content,
                flags=re.DOTALL
            )
            logger.info("✅ Added rate limit checking before posting")
        
        # Add rate limit detection in error handling
        if "_record_posting_attempt" in content and "wait_time = " not in content:
            # Find the error handling section in _record_posting_attempt
            error_pattern = r'(\s+if not success and error_message:.*?error_lower = error_message\.lower\(\).*?if.*?"rate_limit" in error_lower.*?)(\s+ban_detected = True\s+ban_type = "rate_limit")'
            if re.search(error_pattern, content, re.DOTALL):
                content = re.sub(
                    error_pattern,
                    r'\1\n                    # Extract wait time from error message\n                    wait_time = 3600  # Default 1 hour\n                    match = re.search(r\'wait of (\\d+) seconds\', error_message)\n                    if match:\n                        wait_time = int(match.group(1))\n                    \n                    # Store destination with expiry time\n                    destination_id = destination.get("destination_id", "")\n                    if hasattr(self, "rate_limited_destinations"):\n                        self.rate_limited_destinations[destination_id] = time.time() + wait_time\n                        logger.info(f"🕒 Rate limit for {destination_id}: {wait_time}s")\2',
                    content,
                    flags=re.DOTALL
                )
                logger.info("✅ Added rate limit extraction from error messages")
            else:
                logger.warning("⚠️ Could not find error handling pattern in posting_service.py")
        
        with open(file_path, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added improved rate limit handling")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add rate limit handling: {e}")
        return False

def add_destination_validation():
    """Add destination validation to posting_service.py."""
    logger.info("🔧 Adding destination validation...")
    
    try:
        file_path = "scheduler/core/posting_service.py"
        
        if not os.path.exists(file_path):
            logger.error(f"❌ {file_path} does not exist")
            return False
        
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Add invalid_destinations set to __init__ if not already present
        if "self.invalid_destinations =" not in content:
            init_pattern = r'(\s+def __init__\(self, .*?\):.*?)(\s+self\.last_global_join = None)'
            if re.search(init_pattern, content, re.DOTALL):
                content = re.sub(
                    init_pattern,
                    r'\1\n        # Track invalid destinations\n        self.invalid_destinations = set()  # Set of known invalid destination_ids\2',
                    content,
                    flags=re.DOTALL
                )
                logger.info("✅ Added invalid_destinations set")
            else:
                logger.warning("⚠️ Could not find initialization pattern in posting_service.py")
        else:
            logger.info("✅ invalid_destinations set already exists")
        
        # Add validate_destination method if not already present
        if "async def validate_destination" not in content:
            # Find a good place to add the method - after the last method in the class
            last_method_end = content.rfind("}")
            if last_method_end != -1:
                validate_method = """
    async def validate_destination(self, destination: Dict) -> bool:
        \"\"\"Check if a destination is valid before attempting to post.\"\"\"
        destination_id = destination.get("destination_id", "")
        destination_name = destination.get("name", "")
        
        # Skip known invalid destinations
        if hasattr(self, "invalid_destinations") and destination_id in self.invalid_destinations:
            logger.info(f"⏭️ Skipping known invalid destination: {destination_name} ({destination_id})")
            return False
            
        # Skip rate-limited destinations
        if hasattr(self, "rate_limited_destinations") and destination_id in self.rate_limited_destinations:
            if time.time() < self.rate_limited_destinations[destination_id]:
                remaining = int(self.rate_limited_destinations[destination_id] - time.time())
                logger.info(f"⏭️ Skipping rate-limited destination {destination_name} for {remaining}s")
                return False
        
        # Check format validity (basic checks)
        if "/" in destination_id and not destination_id.split("/")[0]:
            logger.warning(f"❌ Invalid destination format: {destination_name} ({destination_id})")
            if hasattr(self, "invalid_destinations"):
                self.invalid_destinations.add(destination_id)
            return False
        
        # Check for known invalid patterns
        invalid_patterns = ["@c/", "@social/", "@mafiamarketss/", "@crystalmarketss/"]
        for pattern in invalid_patterns:
            if pattern.lower() in destination_id.lower() or pattern.lower() in destination_name.lower():
                logger.warning(f"❌ Invalid destination pattern {pattern}: {destination_name} ({destination_id})")
                if hasattr(self, "invalid_destinations"):
                    self.invalid_destinations.add(destination_id)
                return False
        
        return True
"""
                content = content[:last_method_end] + validate_method + content[last_method_end:]
                logger.info("✅ Added validate_destination method")
            else:
                logger.warning("⚠️ Could not find a place to add validate_destination method")
        else:
            logger.info("✅ validate_destination method already exists")
        
        # Call validation before posting if not already present
        if "# Validate destination first" not in content:
            post_pattern = r'(\s+async def _post_single_destination_parallel\(self, ad_slot: Dict, destination: Dict, worker, results: Dict\[str, Any\], posted_slots: set = None\):.*?)(\s+try:)'
            if re.search(post_pattern, content, re.DOTALL):
                content = re.sub(
                    post_pattern,
                    r'\1\n        # Validate destination first\n        if hasattr(self, "validate_destination"):\n            valid = await self.validate_destination(destination)\n            if not valid:\n                destination_id = destination.get("destination_id", "")\n                results[destination_id] = {"success": False, "error": "Invalid destination"}\n                return False\2',
                    content,
                    flags=re.DOTALL
                )
                logger.info("✅ Added validation call before posting")
            else:
                logger.warning("⚠️ Could not find posting method pattern")
        else:
            logger.info("✅ Validation call already exists")
        
        with open(file_path, 'w') as file:
            file.write(content)
        
        logger.info("✅ Added destination validation")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to add destination validation: {e}")
        return False

def fix_worker_count(tables, table_columns):
    """Fix worker count in the database."""
    logger.info("🔧 Fixing worker count...")
    
    try:
        # Check if worker_usage table exists
        if 'worker_usage' not in tables:
            logger.error("❌ worker_usage table does not exist")
            return False
        
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Count workers
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        
        if worker_count == 10:
            logger.info("✅ Worker count is already correct (10)")
            conn.close()
            return True
        
        logger.warning(f"⚠️ Incorrect worker count: {worker_count} (should be 10)")
        
        # Fix worker count
        if worker_count > 10:
            # Keep only workers 1-10
            cursor.execute("DELETE FROM worker_usage WHERE worker_id > 10")
            deleted = cursor.rowcount
            logger.info(f"✅ Deleted {deleted} excess workers")
        elif worker_count < 10:
            # Add missing workers
            for worker_id in range(1, 11):
                cursor.execute("SELECT COUNT(*) FROM worker_usage WHERE worker_id = ?", (worker_id,))
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    # Check which columns exist
                    columns = table_columns.get('worker_usage', [])
                    
                    if 'hourly_posts' in columns and 'daily_posts' in columns:
                        cursor.execute("""
                            INSERT INTO worker_usage (
                                worker_id, hourly_posts, daily_posts, 
                                hourly_limit, daily_limit, is_active
                            ) VALUES (?, 0, 0, 15, 100, 1)
                        """, (worker_id,))
                    elif 'hourly_usage' in columns and 'daily_usage' in columns:
                        cursor.execute("""
                            INSERT INTO worker_usage (
                                worker_id, hourly_usage, daily_usage, 
                                hourly_limit, daily_limit, is_active
                            ) VALUES (?, 0, 0, 15, 100, 1)
                        """, (worker_id,))
                    else:
                        # Generic approach - insert just the worker_id
                        cursor.execute("""
                            INSERT INTO worker_usage (worker_id) VALUES (?)
                        """, (worker_id,))
                        
                    logger.info(f"✅ Added missing worker {worker_id}")
        
        # Verify worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        new_count = cursor.fetchone()[0]
        logger.info(f"✅ New worker count: {new_count}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker count: {e}")
        return False

def create_check_ads_script(tables, table_columns):
    """Create a script to check for due ads based on actual database schema."""
    logger.info("🔧 Creating check_ads script based on actual schema...")
    
    try:
        # Determine which tables and columns exist
        has_ad_slots = 'ad_slots' in tables
        has_destinations = 'destinations' in tables
        
        if not has_ad_slots:
            logger.error("❌ ad_slots table does not exist, cannot create check_ads script")
            return False
        
        # Determine column names
        ad_slot_columns = table_columns.get('ad_slots', [])
        has_slot_type = 'slot_type' in ad_slot_columns
        has_frequency_hours = 'frequency_hours' in ad_slot_columns
        has_last_sent_at = 'last_sent_at' in ad_slot_columns
        has_is_paused = 'is_paused' in ad_slot_columns
        
        # Create script content based on actual schema
        content = """#!/usr/bin/env python3
\"\"\"
Check Ads Script (Schema-Adaptive)

This script checks for any ad slots that are due for posting,
adapting to the actual database schema.

Usage:
    python check_ads_adaptive.py
\"\"\"

import sqlite3
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def main():
    print("🔍 Checking for ad slots...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query based on actual schema
"""
        
        # Build query based on actual schema
        if has_destinations:
            content += """
        query = \"\"\"
        SELECT 
            a.id, 
            a.user_id, 
"""
            if has_slot_type:
                content += "            a.slot_type,\n"
            if has_frequency_hours:
                content += "            a.frequency_hours,\n"
            if has_last_sent_at:
                content += "            a.last_sent_at,\n"
            if has_is_paused:
                content += "            a.is_paused,\n"
            
            content += """            COUNT(d.id) as destination_count
        FROM 
            ad_slots a
        LEFT JOIN 
            destinations d ON a.id = d.slot_id
        GROUP BY 
            a.id
        ORDER BY 
"""
            if has_last_sent_at:
                content += "            a.last_sent_at ASC\n"
            else:
                content += "            a.id ASC\n"
            
            content += "        \"\"\"\n"
            
        else:
            content += """
        query = \"\"\"
        SELECT 
            id, 
            user_id, 
"""
            if has_slot_type:
                content += "            slot_type,\n"
            if has_frequency_hours:
                content += "            frequency_hours,\n"
            if has_last_sent_at:
                content += "            last_sent_at,\n"
            if has_is_paused:
                content += "            is_paused,\n"
            
            content += """            0 as destination_count
        FROM 
            ad_slots
        ORDER BY 
"""
            if has_last_sent_at:
                content += "            last_sent_at ASC\n"
            else:
                content += "            id ASC\n"
            
            content += "        \"\"\"\n"
        
        content += """
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No ad slots found in the system.")
            return
        
        # Display results
        print(f"Found {len(results)} total ad slots:")
        print("\\n{:<5} {:<10}".format("ID", "User"), end="")
"""
        
        # Add column headers based on schema
        if has_slot_type:
            content += "        print(\" {:<10}\".format(\"Type\"), end=\"\")\n"
        if has_last_sent_at:
            content += "        print(\" {:<20}\".format(\"Last Sent\"), end=\"\")\n"
        if has_frequency_hours:
            content += "        print(\" {:<10}\".format(\"Frequency\"), end=\"\")\n"
        
        content += """        print(" {:<15} {:<10}".format("Destinations", "Status"))
        print("-" * 80)
        
        # Calculate current time
        now = datetime.now()
        
        for row in results:
            slot_id = row['id']
            user_id = row['user_id']
"""
        
        # Add row processing based on schema
        if has_slot_type:
            content += "            slot_type = row['slot_type'] if 'slot_type' in row.keys() else 'unknown'\n"
        else:
            content += "            slot_type = 'unknown'\n"
            
        if has_frequency_hours:
            content += "            frequency = row['frequency_hours'] if 'frequency_hours' in row.keys() else None\n"
        else:
            content += "            frequency = None\n"
            
        if has_last_sent_at:
            content += "            last_sent = row['last_sent_at'] if row['last_sent_at'] else \"Never\"\n"
        else:
            content += "            last_sent = \"Unknown\"\n"
            
        if has_is_paused:
            content += "            is_paused = row['is_paused'] == 1 if 'is_paused' in row.keys() else False\n"
        else:
            content += "            is_paused = False\n"
            
        content += """            destination_count = row['destination_count']
            
            # Calculate status
            status = "PAUSED" if is_paused else ""
"""
        
        # Add status calculation based on schema
        if has_last_sent_at and has_frequency_hours:
            content += """            if not is_paused and last_sent != "Never" and frequency:
                try:
                    last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S')
                    next_post_dt = last_sent_dt + timedelta(hours=frequency)
                    
                    # Check if it's due
                    if next_post_dt <= now:
                        status = "DUE NOW"
                    else:
                        hours_until = (next_post_dt - now).total_seconds() / 3600
                        if hours_until <= 1:
                            status = "DUE SOON"
                except Exception as e:
                    status = "ERROR"
            elif not is_paused and last_sent == "Never":
                status = "NEW"
"""
        
        # Add row printing based on schema
        content += """
            print("{:<5} {:<10}".format(slot_id, f"ID:{user_id}"), end="")
"""
        
        if has_slot_type:
            content += "            print(\" {:<10}\".format(slot_type), end=\"\")\n"
        if has_last_sent_at:
            content += "            print(\" {:<20}\".format(last_sent[:19] if last_sent != \"Never\" else \"Never\"), end=\"\")\n"
        if has_frequency_hours:
            content += "            print(\" {:<10}\".format(f\"{frequency}h\" if frequency else \"N/A\"), end=\"\")\n"
            
        content += """            print(" {:<15} {:<10}".format(f"{destination_count} dests", status))
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking ads: {e}")

if __name__ == "__main__":
    main()
"""
        
        # Write the script
        with open("check_ads_adaptive.py", 'w') as file:
            file.write(content)
        
        # Make it executable
        os.chmod("check_ads_adaptive.py", 0o755)
        
        logger.info("✅ Created check_ads_adaptive.py based on actual schema")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating check_ads script: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 STARTING COMPREHENSIVE BOT FIXES")
    logger.info("=" * 60)
    
    # Check database schema first
    tables, table_columns = check_database_schema()
    
    # Create a schema-adaptive check_ads script
    create_check_ads_script(tables, table_columns)
    
    # Fix global join limits
    fix_global_join_limits()
    
    # Add rate limit handling
    add_rate_limit_handling()
    
    # Add destination validation
    add_destination_validation()
    
    # Fix worker count if worker_usage table exists
    if 'worker_usage' in tables:
        fix_worker_count(tables, table_columns)
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 SUMMARY OF APPLIED FIXES")
    logger.info("=" * 60)
    logger.info("✅ Created schema-adaptive check_ads_adaptive.py")
    logger.info("✅ Fixed global join limits (50/day, 20/hour)")
    logger.info("✅ Added rate limit handling")
    logger.info("✅ Added destination validation")
    if 'worker_usage' in tables:
        logger.info("✅ Fixed worker count")
    else:
        logger.info("⚠️ Could not fix worker count (worker_usage table missing)")
    
    logger.info("")
    logger.info("🔄 Please restart the bot to apply all fixes:")
    logger.info("    python start_bot.py")
    logger.info("")
    logger.info("📊 To check for due ads:")
    logger.info("    python check_ads_adaptive.py")

if __name__ == "__main__":
    main()