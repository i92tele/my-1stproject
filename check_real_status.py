#!/usr/bin/env python3
"""
Check Real Status
Check the actual status of ad slots and their destinations
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    print("🔍 CHECKING REAL STATUS")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection for direct SQL
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        print("📝 AD SLOTS STATUS:")
        print("-" * 30)
        
        # Check ad_slots table
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        active_slots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ad_slots")
        total_slots = cursor.fetchone()[0]
        
        print(f"  - Total ad slots: {total_slots}")
        print(f"  - Active ad slots: {active_slots}")
        
        # Show active slots details
        cursor.execute("""
            SELECT id, user_id, slot_number, is_active, category 
            FROM ad_slots 
            WHERE is_active = 1
        """)
        active_slots_data = cursor.fetchall()
        
        for slot in active_slots_data:
            slot_id, user_id, slot_number, is_active, category = slot
            print(f"    ✅ Slot {slot_id}: User {user_id}, Slot {slot_number}, Category: {category}")
        
        print("\n🎯 DESTINATIONS STATUS:")
        print("-" * 30)
        
        # Check destinations table
        cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
        active_destinations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM destinations")
        total_destinations = cursor.fetchone()[0]
        
        print(f"  - Total destinations: {total_destinations}")
        print(f"  - Active destinations: {active_destinations}")
        
        # Show active destinations
        cursor.execute("SELECT id, name, url, status FROM destinations WHERE status = 'active'")
        active_dest_data = cursor.fetchall()
        
        for dest in active_dest_data:
            dest_id, name, url, status = dest
            print(f"    ✅ Destination {dest_id}: {name} ({url})")
        
        print("\n🔗 SLOT DESTINATIONS:")
        print("-" * 30)
        
        # Check slot_destinations table (this is what the scheduler actually uses)
        cursor.execute("SELECT COUNT(*) FROM slot_destinations WHERE is_active = 1")
        active_slot_destinations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM slot_destinations")
        total_slot_destinations = cursor.fetchone()[0]
        
        print(f"  - Total slot destinations: {total_slot_destinations}")
        print(f"  - Active slot destinations: {active_slot_destinations}")
        
        # Show slot destinations for active slots
        cursor.execute("""
            SELECT sd.id, sd.slot_id, sd.destination_id, sd.destination_name, sd.is_active
            FROM slot_destinations sd
            JOIN ad_slots a ON sd.slot_id = a.id
            WHERE a.is_active = 1 AND sd.is_active = 1
        """)
        slot_dest_data = cursor.fetchall()
        
        for sd in slot_dest_data:
            sd_id, slot_id, dest_id, dest_name, is_active = sd
            print(f"    ✅ Slot {slot_id} -> {dest_id} ({dest_name})")
        
        print("\n👥 WORKERS STATUS:")
        print("-" * 30)
        
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM workers")
        total_workers = cursor.fetchone()[0]
        
        print(f"  - Total workers: {total_workers}")
        print(f"  - Active workers: {active_workers}")
        
        print("\n💳 SUBSCRIPTIONS STATUS:")
        print("-" * 30)
        
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active_subs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        total_subs = cursor.fetchone()[0]
        
        print(f"  - Total subscriptions: {total_subs}")
        print(f"  - Active subscriptions: {active_subs}")
        
        # Show active subscriptions
        cursor.execute("SELECT user_id, tier, status, expires_at FROM subscriptions WHERE status = 'active'")
        active_subs_data = cursor.fetchall()
        
        for sub in active_subs_data:
            user_id, tier, status, expires_at = sub
            print(f"    ✅ User {user_id}: {tier} tier, expires: {expires_at}")
        
        print("\n📊 SCHEDULER READINESS:")
        print("-" * 30)
        
        if active_workers > 0 and active_slots > 0 and active_slot_destinations > 0 and active_subs > 0:
            print("✅ SCHEDULER READY!")
            print(f"🚀 Can post with {active_workers} workers to {active_slot_destinations} destinations")
        else:
            print("❌ SCHEDULER NOT READY:")
            if active_workers == 0:
                print("  - No active workers")
            if active_slots == 0:
                print("  - No active ad slots")
            if active_slot_destinations == 0:
                print("  - No active slot destinations")
            if active_subs == 0:
                print("  - No active subscriptions")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
