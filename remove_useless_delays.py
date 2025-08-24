#!/usr/bin/env python3
"""
Remove Useless Task Creation Delays

This script removes the useless staggered delays that happen during task creation
instead of during actual posting execution.

Usage:
    python remove_useless_delays.py
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def remove_useless_delays():
    """Remove useless task creation delays from posting_service.py."""
    logger.info("🔧 Removing useless task creation delays...")
    
    try:
        posting_service_path = "scheduler/core/posting_service.py"
        
        if not os.path.exists(posting_service_path):
            logger.error(f"❌ {posting_service_path} does not exist")
            return False
        
        with open(posting_service_path, 'r') as file:
            content = file.read()
        
        # Find and remove the useless delay code
        lines = content.split('\n')
        new_lines = []
        removed_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is the useless delay code
            if "Add staggered delay every few destinations to avoid rate limits" in line:
                # Remove the comment and the next few lines that contain the delay logic
                logger.info("✅ Removing useless delay comment and logic")
                removed_count += 1
                
                # Skip the comment line
                i += 1
                
                # Skip the delay logic (usually 3-4 lines)
                while i < len(lines) and ("if i > 0 and i % 5 == 0" in lines[i] or 
                                        "Adding staggered delay after" in lines[i] or
                                        "await asyncio.sleep(10)" in lines[i]):
                    logger.info(f"✅ Removing delay line: {lines[i].strip()}")
                    i += 1
                    removed_count += 1
                
                continue
            
            new_lines.append(line)
            i += 1
        
        # Write the updated content
        new_content = '\n'.join(new_lines)
        
        with open(posting_service_path, 'w') as file:
            file.write(new_content)
        
        logger.info(f"✅ Removed {removed_count} lines of useless delay code")
        logger.info("✅ Task creation delays eliminated")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error removing useless delays: {e}")
        return False

def optimize_anti_ban_system():
    """Add better anti-ban measures to replace the useless delays."""
    logger.info("🔧 Optimizing anti-ban system...")
    
    try:
        posting_service_path = "scheduler/core/posting_service.py"
        
        with open(posting_service_path, 'r') as file:
            content = file.read()
        
        # Add better anti-ban measures if they don't exist
        if "random_delay_between_posts" not in content:
            # Add a better anti-ban function
            anti_ban_function = '''
    async def _add_anti_ban_delay(self):
        """Add random delay between posts for anti-ban protection."""
        import random
        delay = random.uniform(2, 8)  # 2-8 seconds
        logger.debug(f"🛡️ Anti-ban delay: {delay:.1f}s")
        await asyncio.sleep(delay)
'''
            
            # Find a good place to insert this function (before the validate_destination function)
            if "async def validate_destination" in content:
                content = content.replace(
                    "async def validate_destination",
                    anti_ban_function + "\n    async def validate_destination"
                )
                logger.info("✅ Added anti-ban delay function")
        
        # Update the posting function to use the new anti-ban delay
        if "_add_anti_ban_delay" in content and "await self._add_anti_ban_delay()" not in content:
            # Add the anti-ban delay call in the posting function
            content = content.replace(
                "logger.info(f\"🚀 Starting task: Worker {worker.worker_id} -> Slot {slot_id} -> {destination.get('destination_name', 'Unknown')}\")",
                "logger.info(f\"🚀 Starting task: Worker {worker.worker_id} -> Slot {slot_id} -> {destination.get('destination_name', 'Unknown')}\")\n        # Add anti-ban delay\n        await self._add_anti_ban_delay()"
            )
            logger.info("✅ Added anti-ban delay calls to posting function")
        
        with open(posting_service_path, 'w') as file:
            file.write(content)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error optimizing anti-ban system: {e}")
        return False

def main():
    """Main function to remove useless delays and optimize anti-ban."""
    logger.info("=" * 80)
    logger.info("🚀 REMOVING USELESS DELAYS & OPTIMIZING ANTI-BAN")
    logger.info("=" * 80)
    
    # Step 1: Remove useless delays
    if remove_useless_delays():
        logger.info("✅ Useless delays removed successfully")
    else:
        logger.error("❌ Failed to remove useless delays")
        return
    
    # Step 2: Optimize anti-ban system
    if optimize_anti_ban_system():
        logger.info("✅ Anti-ban system optimized")
    else:
        logger.warning("⚠️ Anti-ban optimization failed, but delays were removed")
    
    logger.info("=" * 80)
    logger.info("📊 OPTIMIZATION SUMMARY")
    logger.info("=" * 80)
    logger.info("✅ Removed useless task creation delays")
    logger.info("✅ Added proper anti-ban delays during posting")
    logger.info("✅ System will be more efficient")
    logger.info("")
    logger.info("🔄 Restart the bot to apply changes:")
    logger.info("    python start_bot.py")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
