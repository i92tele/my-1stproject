#!/usr/bin/env python3
"""
Fix Destinations
Check and fix destinations issue
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DestinationsFixer:
    """Fix destinations issues."""
    
    def __init__(self):
        self.logger = logger
    
    async def check_destinations(self):
        """Check destinations status."""
        print("🎯 CHECKING DESTINATIONS")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get all destinations
            destinations = await db.get_destinations()
            
            print(f"📊 Total destinations: {len(destinations)}")
            
            if destinations:
                print("📋 Destination details:")
                for dest in destinations:
                    print(f"  - {dest.get('name', 'Unknown')}: {dest.get('status', 'unknown')}")
            
            # Check for active destinations
            active_destinations = [d for d in destinations if d.get('status') == 'active']
            print(f"✅ Active destinations: {len(active_destinations)}")
            
            await db.close()
            
            return destinations, len(active_destinations)
            
        except Exception as e:
            print(f"❌ Error checking destinations: {e}")
            return [], 0
    
    async def check_ad_slots(self):
        """Check ad slots and their destinations."""
        print("\n📝 CHECKING AD SLOTS")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get all ad slots
            ad_slots = await db.get_ad_slots()
            
            print(f"📊 Total ad slots: {len(ad_slots)}")
            
            active_slots = [slot for slot in ad_slots if slot.get('status') == 'active']
            print(f"✅ Active ad slots: {len(active_slots)}")
            
            if active_slots:
                print("📋 Active slot details:")
                for slot in active_slots:
                    user_id = slot.get('user_id', 'Unknown')
                    content = slot.get('content', 'No content')[:50] + "..." if len(slot.get('content', '')) > 50 else slot.get('content', 'No content')
                    last_posted = slot.get('last_posted', 'Never')
                    print(f"  - User {user_id}: {content} (Last: {last_posted})")
            
            await db.close()
            
            return ad_slots, len(active_slots)
            
        except Exception as e:
            print(f"❌ Error checking ad slots: {e}")
            return [], 0
    
    async def check_user_subscriptions(self):
        """Check user subscriptions."""
        print("\n👥 CHECKING USER SUBSCRIPTIONS")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            # Get all subscriptions
            subscriptions = await db.get_all_subscriptions()
            
            print(f"📊 Total subscriptions: {len(subscriptions)}")
            
            active_subscriptions = [sub for sub in subscriptions if sub.get('status') == 'active']
            print(f"✅ Active subscriptions: {len(active_subscriptions)}")
            
            if active_subscriptions:
                print("📋 Active subscription details:")
                for sub in active_subscriptions:
                    user_id = sub.get('user_id', 'Unknown')
                    plan = sub.get('plan', 'Unknown')
                    expires_at = sub.get('expires_at', 'Unknown')
                    print(f"  - User {user_id}: {plan} (Expires: {expires_at})")
            
            await db.close()
            
            return subscriptions, len(active_subscriptions)
            
        except Exception as e:
            print(f"❌ Error checking subscriptions: {e}")
            return [], 0
    
    async def create_sample_destinations(self):
        """Create sample destinations if none exist."""
        print("\n🔧 CREATING SAMPLE DESTINATIONS")
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
            
            # Check if destinations table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='destinations'
            """)
            
            if not cursor.fetchone():
                print("❌ Destinations table doesn't exist")
                await db.close()
                return False
            
            # Check if we have any destinations
            cursor.execute("SELECT COUNT(*) FROM destinations")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("📝 No destinations found, creating sample destinations...")
                
                # Create sample destinations
                sample_destinations = [
                    ("Telegram Channel 1", "https://t.me/sample_channel_1", "active"),
                    ("Telegram Group 1", "https://t.me/sample_group_1", "active"),
                    ("Telegram Channel 2", "https://t.me/sample_channel_2", "active"),
                ]
                
                for name, url, status in sample_destinations:
                    cursor.execute("""
                        INSERT INTO destinations (name, url, status, created_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (name, url, status))
                
                conn.commit()
                print(f"✅ Created {len(sample_destinations)} sample destinations")
            else:
                print(f"✅ Found {count} existing destinations")
            
            await db.close()
            return True
            
        except Exception as e:
            print(f"❌ Error creating destinations: {e}")
            return False
    
    async def activate_destinations(self):
        """Activate all destinations."""
        print("\n🔧 ACTIVATING DESTINATIONS")
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
            
            # Activate all destinations
            cursor.execute("""
                UPDATE destinations 
                SET status = 'active' 
                WHERE status != 'active'
            """)
            
            activated_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Activated {activated_count} destinations")
            
            await db.close()
            
            return activated_count
            
        except Exception as e:
            print(f"❌ Error activating destinations: {e}")
            return 0

async def main():
    """Main function."""
    fixer = DestinationsFixer()
    
    # Check current status
    destinations, active_destinations = await fixer.check_destinations()
    ad_slots, active_slots = await fixer.check_ad_slots()
    subscriptions, active_subscriptions = await fixer.check_user_subscriptions()
    
    # Create sample destinations if needed
    if len(destinations) == 0:
        await fixer.create_sample_destinations()
    
    # Activate destinations
    activated_count = await fixer.activate_destinations()
    
    # Check final status
    destinations, active_destinations = await fixer.check_destinations()
    
    print("\n📊 DESTINATIONS FIX SUMMARY")
    print("=" * 50)
    print("Current status:")
    print(f"1. 📝 Active ad slots: {active_slots}")
    print(f"2. 🎯 Active destinations: {active_destinations}")
    print(f"3. 👥 Active subscriptions: {active_subscriptions}")
    print(f"4. 🔧 Destinations activated: {activated_count}")
    
    if active_destinations > 0 and active_slots > 0:
        print("\n✅ SUCCESS: Destinations and ad slots are ready!")
        print("🚀 Scheduler should be able to post now")
    else:
        print("\n❌ ISSUES FOUND:")
        if active_slots == 0:
            print("  - No active ad slots")
        if active_destinations == 0:
            print("  - No active destinations")
        print("🔧 Need to create ad slots or destinations")

if __name__ == "__main__":
    asyncio.run(main())

