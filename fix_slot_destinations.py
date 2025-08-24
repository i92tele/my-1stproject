#!/usr/bin/env python3
"""
Fix Admin Slot Destinations

This script fixes the issue where the posting service can't find destinations for admin slots.
The issue is that get_slot_destinations() isn't properly handling admin slot destinations.
"""

import asyncio
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the database manager
try:
    from src.database.manager import DatabaseManager
except ImportError:
    logger.error("Failed to import DatabaseManager. Make sure you're in the project root directory.")
    sys.exit(1)

async def fix_get_slot_destinations():
    """Fix the get_slot_destinations method to properly handle admin slots."""
    logger.info("🔧 FIXING GET_SLOT_DESTINATIONS METHOD")
    logger.info("=" * 60)
    
    # Read the current file
    try:
        with open('src/database/manager.py', 'r') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"❌ Error reading manager.py: {e}")
        return False
    
    # Find the get_slot_destinations method
    method_start = None
    method_end = None
    for i, line in enumerate(lines):
        if "async def get_slot_destinations" in line:
            method_start = i
        elif method_start is not None and line.strip().startswith("async def "):
            method_end = i
            break
    
    if method_start is None:
        logger.error("❌ Could not find get_slot_destinations method")
        return False
    
    if method_end is None:
        method_end = len(lines)
    
    # Extract the current method
    current_method = "".join(lines[method_start:method_end])
    logger.info(f"📋 Found get_slot_destinations method at line {method_start}")
    
    # Create the fixed method
    fixed_method = """async def get_slot_destinations(self, slot_id: int, slot_type: str = 'user') -> List[Dict[str, Any]]:
        """Get destinations for a slot (updated method with slot_type support)."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if slot_type == 'admin':
                    table_name = 'admin_slot_destinations'
                else:
                    table_name = 'slot_destinations'
                
                cursor.execute(f'''
                    SELECT * FROM {table_name}
                    WHERE slot_id = ? AND is_active = 1
                    ORDER BY created_at
                ''', (slot_id,))
                
                destinations = [dict(row) for row in cursor.fetchall()]
                conn.close()
                
                # Log the results for debugging
                self.logger.info(f"get_slot_destinations({slot_id}, {slot_type}): Found {len(destinations)} destinations")
                
                return destinations
                
            except Exception as e:
                self.logger.error(f"Error getting slot destinations: {e}")
                return []
"""
    
    # Replace the method
    new_lines = lines[:method_start] + [fixed_method] + lines[method_end:]
    
    # Write the fixed file
    try:
        with open('src/database/manager.py', 'w') as f:
            f.writelines(new_lines)
        logger.info("✅ Successfully updated get_slot_destinations method")
        return True
    except Exception as e:
        logger.error(f"❌ Error writing manager.py: {e}")
        return False

async def restart_services():
    """Restart the bot services."""
    logger.info("\n🔄 RESTARTING SERVICES")
    logger.info("=" * 60)
    
    try:
        import os
        
        # Stop services
        logger.info("Stopping services...")
        os.system("pkill -f 'python3 bot.py'")
        os.system("pkill -f 'python3 scheduler/scheduler.py'")
        os.system("pkill -f 'python3 payment_monitor.py'")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Start services
        logger.info("Starting services...")
        os.system("nohup python3 bot.py > bot.log 2>&1 &")
        os.system("nohup python3 scheduler/scheduler.py > scheduler.log 2>&1 &")
        os.system("nohup python3 payment_monitor.py > payment_monitor.log 2>&1 &")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Check if services are running
        main_bot_pid = os.popen('pgrep -f "python3 bot.py"').read().strip()
        scheduler_pid = os.popen('pgrep -f "python3 scheduler/scheduler.py"').read().strip()
        payment_pid = os.popen('pgrep -f "python3 payment_monitor.py"').read().strip()
        
        if main_bot_pid and scheduler_pid and payment_pid:
            logger.info(f"✅ All services restarted successfully")
            logger.info(f"Main Bot PID: {main_bot_pid}")
            logger.info(f"Scheduler PID: {scheduler_pid}")
            logger.info(f"Payment Monitor PID: {payment_pid}")
            return True
        else:
            logger.error("❌ Failed to restart all services")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error restarting services: {e}")
        return False

async def main():
    """Main function."""
    logger.info("🔧 ADMIN SLOT DESTINATIONS FIX")
    logger.info("=" * 60)
    
    # Fix the get_slot_destinations method
    fixed = await fix_get_slot_destinations()
    
    if fixed:
        # Ask if user wants to restart services
        print("\n🔄 Do you want to restart the bot services?")
        print("This is recommended to apply the fix.")
        choice = input("Restart services? (y/n): ")
        
        if choice.lower() == 'y':
            await restart_services()
    
    logger.info("\n🔍 FIX COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
