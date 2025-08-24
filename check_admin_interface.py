#!/usr/bin/env python3
"""
Check Admin Interface Status

This script checks the status of the admin interface components:
- Admin slots
- System check functionality
- Revenue stats functionality
- Worker status

Usage:
    python check_admin_interface.py
"""

import sqlite3
import logging
import os
import importlib.util
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def check_admin_slots():
    """Check admin slots in the database."""
    logger.info("🔍 Checking admin slots...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if admin_ad_slots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
        if cursor.fetchone() is None:
            logger.error("❌ admin_ad_slots table does not exist")
            conn.close()
            return False
        
        # Count admin slots
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
        admin_slot_count = cursor.fetchone()[0]
        
        if admin_slot_count == 0:
            logger.warning("⚠️ No admin slots found")
        else:
            logger.info(f"✅ Found {admin_slot_count} admin slots")
            
            # Get admin slots
            cursor.execute("""
                SELECT 
                    id, 
                    slot_number,
                    is_active,
                    is_paused,
                    last_sent_at
                FROM 
                    admin_ad_slots
                ORDER BY 
                    id
            """)
            
            admin_slots = cursor.fetchall()
            
            print("\nAdmin Slots:")
            print(f"{'ID':<5} | {'Number':<6} | {'Active':<6} | {'Paused':<6} | {'Last Sent'}")
            print("-" * 60)
            
            for slot in admin_slots:
                slot_id = slot['id']
                slot_number = slot['slot_number']
                is_active = "Yes" if slot['is_active'] == 1 else "No"
                is_paused = "Yes" if slot['is_paused'] == 1 else "No"
                last_sent = slot['last_sent_at'] if slot['last_sent_at'] else "Never"
                
                print(f"{slot_id:<5} | {slot_number:<6} | {is_active:<6} | {is_paused:<6} | {last_sent}")
        
        # Check admin slot destinations
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_slot_destinations'")
        if cursor.fetchone() is None:
            logger.error("❌ admin_slot_destinations table does not exist")
        else:
            cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations")
            dest_count = cursor.fetchone()[0]
            logger.info(f"✅ Found {dest_count} admin slot destinations")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking admin slots: {e}")
        return False

def check_admin_commands():
    """Check admin commands in the codebase."""
    logger.info("🔍 Checking admin commands...")
    
    try:
        admin_commands_path = "commands/admin_commands.py"
        
        if not os.path.exists(admin_commands_path):
            logger.error(f"❌ {admin_commands_path} does not exist")
            return False
        
        # Load the module
        spec = importlib.util.spec_from_file_location("admin_commands", admin_commands_path)
        admin_commands = importlib.util.module_from_spec(spec)
        sys.modules["admin_commands"] = admin_commands
        spec.loader.exec_module(admin_commands)
        
        # Check for required functions
        required_functions = [
            "show_admin_stats",
            "show_revenue_stats", 
            "show_system_status", 
            "show_worker_status",
            "show_slot_stats"
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if not hasattr(admin_commands, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            logger.warning(f"⚠️ Missing admin functions: {', '.join(missing_functions)}")
        else:
            logger.info("✅ All required admin functions exist")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking admin commands: {e}")
        return False

def check_database_methods():
    """Check database methods in the codebase."""
    logger.info("🔍 Checking database methods...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check tables needed for admin interface
        required_tables = [
            "worker_usage",
            "worker_cooldowns",
            "worker_bans",
            "worker_activity_log",
            "admin_ad_slots",
            "admin_slot_destinations",
            "admin_slot_posts",
            "payments",
            "subscriptions"
        ]
        
        missing_tables = []
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone() is None:
                missing_tables.append(table)
        
        if missing_tables:
            logger.warning(f"⚠️ Missing required tables: {', '.join(missing_tables)}")
        else:
            logger.info("✅ All required tables exist")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking database methods: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 CHECKING ADMIN INTERFACE STATUS")
    logger.info("=" * 60)
    
    # Check admin slots
    check_admin_slots()
    
    # Check admin commands
    check_admin_commands()
    
    # Check database methods
    check_database_methods()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 ADMIN INTERFACE STATUS SUMMARY")
    logger.info("=" * 60)
    logger.info("If any issues were found above, you may need to run:")
    logger.info("    python fix_worker_count.py")
    logger.info("")
    logger.info("Then restart the bot:")
    logger.info("    python start_bot.py")

if __name__ == "__main__":
    main()
