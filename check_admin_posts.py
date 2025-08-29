#!/usr/bin/env python3
"""
Check Admin Posts
Check the admin ad slots and their destinations
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
    print("🔍 CHECKING ADMIN POSTS")
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
        
        print("📝 ADMIN AD SLOTS:")
        print("-" * 30)
        
        # Check admin_ad_slots table
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
        active_admin_slots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
        total_admin_slots = cursor.fetchone()[0]
        
        print(f"  - Total admin ad slots: {total_admin_slots}")
        print(f"  - Active admin ad slots: {active_admin_slots}")
        
        # Show active admin slots details
        cursor.execute("""
            SELECT id, slot_number, is_active, interval_minutes, last_sent_at 
            FROM admin_ad_slots 
            WHERE is_active = 1
        """)
        active_admin_slots_data = cursor.fetchall()
        
        for slot in active_admin_slots_data:
            slot_id, slot_number, is_active, interval_minutes, last_sent_at = slot
            print(f"    ✅ Admin Slot {slot_id}: Slot {slot_number}, Interval: {interval_minutes}m, Last: {last_sent_at}")
        
        print("\n🔗 ADMIN SLOT DESTINATIONS:")
        print("-" * 30)
        
        # Check admin_slot_destinations table
        cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations WHERE is_active = 1")
        active_admin_destinations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations")
        total_admin_destinations = cursor.fetchone()[0]
        
        print(f"  - Total admin slot destinations: {total_admin_destinations}")
        print(f"  - Active admin slot destinations: {active_admin_destinations}")
        
        # Show admin slot destinations for active admin slots
        cursor.execute("""
            SELECT asd.id, asd.slot_id, asd.destination_id, asd.destination_name, asd.is_active
            FROM admin_slot_destinations asd
            JOIN admin_ad_slots aas ON asd.slot_id = aas.id
            WHERE aas.is_active = 1 AND asd.is_active = 1
        """)
        admin_dest_data = cursor.fetchall()
        
        for dest in admin_dest_data:
            dest_id, slot_id, dest_id_name, dest_name, is_active = dest
            print(f"    ✅ Admin Slot {slot_id} -> {dest_id_name} ({dest_name})")
        
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
        
        print("\n📊 SCHEDULER READINESS:")
        print("-" * 30)
        
        if active_workers > 0 and active_admin_slots > 0 and active_admin_destinations > 0:
            print("✅ SCHEDULER READY!")
            print(f"🚀 Can post with {active_workers} workers to {active_admin_destinations} admin destinations")
        else:
            print("❌ SCHEDULER NOT READY:")
            if active_workers == 0:
                print("  - No active workers")
            if active_admin_slots == 0:
                print("  - No active admin ad slots")
            if active_admin_destinations == 0:
                print("  - No active admin slot destinations")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
