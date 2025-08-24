#!/usr/bin/env python3
"""
Simple Remove Useless Delays

This script simply removes the useless task creation delays without adding complexity.
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
        
        # Remove the specific useless delay code
        lines_to_remove = [
            "                # Add staggered delay every few destinations to avoid rate limits",
            "                if i > 0 and i % 5 == 0:",
            "                    logger.info(f\"Adding staggered delay after {i} destinations for slot {slot_id}\")",
            "                    await asyncio.sleep(10)  # 10-second pause every 5 destinations"
        ]
        
        lines = content.split('\n')
        new_lines = []
        removed_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line should be removed
            should_remove = False
            for remove_line in lines_to_remove:
                if remove_line in line:
                    should_remove = True
                    break
            
            if should_remove:
                logger.info(f"✅ Removing: {line.strip()}")
                removed_count += 1
                i += 1
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

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 REMOVING USELESS TASK CREATION DELAYS")
    logger.info("=" * 60)
    
    if remove_useless_delays():
        logger.info("✅ Useless delays removed successfully")
        logger.info("")
        logger.info("🎯 Benefits:")
        logger.info("- Faster task creation")
        logger.info("- No more useless delays in logs")
        logger.info("- Better system efficiency")
        logger.info("")
        logger.info("🔄 Restart the bot to apply changes:")
        logger.info("    python start_bot.py")
    else:
        logger.error("❌ Failed to remove useless delays")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
