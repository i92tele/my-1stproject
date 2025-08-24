#!/usr/bin/env python3
"""
CRITICAL FIX: Create missing admin_slot_destinations table

This script fixes the critical issue where admin slots can't post because
the admin_slot_destinations table doesn't exist.

Run this IMMEDIATELY before testing admin slots.
"""

import asyncio
import logging
import sqlite3
from src.database.manager import DatabaseManager
from database_admin_slots import AdminSlotDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_admin_destinations_table():
    """Fix the missing admin_slot_destinations table."""
    print("🚨 CRITICAL FIX: Creating missing admin_slot_destinations table...")
    
    try:
        db_path = "bot_database.db"
        
        # Initialize database manager
        db = DatabaseManager(db_path, logger)
        await db.initialize()
        
        # Initialize admin database
        admin_db = AdminSlotDatabase(db_path, logger)
        
        # Run the migration (now includes table creation)
        success = await admin_db.migrate_admin_slots_table()
        
        if success:
            print("✅ SUCCESS: admin_slot_destinations table created!")
            
            # Verify the table exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_slot_destinations'")
            if cursor.fetchone():
                print("✅ VERIFIED: Table exists in database")
            else:
                print("❌ ERROR: Table still missing after creation")
            conn.close()
            
        else:
            print("❌ FAILED: Could not create admin_slot_destinations table")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        logger.error(f"Critical fix failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚨 CRITICAL DATABASE FIX")
    print("=" * 60)
    asyncio.run(fix_admin_destinations_table())
    print("=" * 60)
    print("🎯 Next steps:")
    print("1. Test admin slots: /admin_slots")
    print("2. Check posting status: /posting_status")
    print("3. Verify admin stats: /admin_stats")
    print("=" * 60)

