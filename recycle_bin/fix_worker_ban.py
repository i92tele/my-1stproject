#!/usr/bin/env python3
"""
Fix Worker 4 Ban Script
Clears the ban for Worker 4 that was mentioned in the error log
"""

import asyncio
import logging
from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_worker_4_ban():
    """Clear the ban for Worker 4."""
    print("🔧 Fixing Worker 4 ban...")
    
    try:
        # Initialize database
        db_path = "bot_database.db"
        db = DatabaseManager(db_path, logger)
        await db.initialize()
        
        # Get all bans for Worker 4
        worker_4_bans = await db.get_worker_bans(worker_id=4, active_only=True)
        
        if not worker_4_bans:
            print("✅ Worker 4 has no active bans in database")
        else:
            print(f"🚫 Found {len(worker_4_bans)} active bans for Worker 4")
            
            # Clear all bans for Worker 4
            cleared_count = 0
            for ban in worker_4_bans:
                success = await db.clear_worker_ban(4, ban['destination_id'])
                if success:
                    cleared_count += 1
                    print(f"   ✅ Cleared ban from {ban['destination_id']}")
                else:
                    print(f"   ❌ Failed to clear ban from {ban['destination_id']}")
            
            print(f"🎉 Cleared {cleared_count}/{len(worker_4_bans)} bans for Worker 4")
        
        # Additional fix: Clear any "supergroups/channels" bans specifically
        print("🔍 Checking for supergroups/channels bans...")
        
        # Get all worker bans and check for the specific error pattern
        all_bans = await db.get_worker_bans(active_only=True)
        supergroup_bans = [ban for ban in all_bans if ban.get('worker_id') == 4 and 
                          ('supergroups' in str(ban.get('ban_reason', '')).lower() or 
                           'channels' in str(ban.get('ban_reason', '')).lower())]
        
        if supergroup_bans:
            print(f"🚫 Found {len(supergroup_bans)} supergroups/channels bans for Worker 4")
            for ban in supergroup_bans:
                success = await db.clear_worker_ban(4, ban['destination_id'])
                if success:
                    print(f"   ✅ Cleared supergroups/channels ban from {ban['destination_id']}")
                else:
                    print(f"   ❌ Failed to clear supergroups/channels ban from {ban['destination_id']}")
        else:
            print("✅ No supergroups/channels bans found for Worker 4")
        
        # Verify ban is cleared
        remaining_bans = await db.get_worker_bans(worker_id=4, active_only=True)
        if not remaining_bans:
            print("✅ Worker 4 is now free of bans and ready to work!")
        else:
            print(f"⚠️ Worker 4 still has {len(remaining_bans)} active bans")
            for ban in remaining_bans:
                print(f"   - {ban['destination_id']}: {ban.get('ban_reason', 'Unknown reason')}")
        
        # Additional recommendations
        print("\n📋 **Recommendations:**")
        print("1. Restart the scheduler to ensure Worker 4 is reactivated")
        print("2. Monitor Worker 4 performance for the next few hours")
        print("3. Consider implementing worker rotation to prevent future bans")
        print("4. Check if Worker 4 needs to rejoin any groups")
        
    except Exception as e:
        print(f"❌ Error fixing Worker 4 ban: {e}")
        logger.error(f"Error fixing Worker 4 ban: {e}")

if __name__ == "__main__":
    asyncio.run(fix_worker_4_ban())
