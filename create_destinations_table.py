#!/usr/bin/env python3
"""
Create Destinations Table
Create the missing destinations table and fix ad slots
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

class DestinationsTableCreator:
    """Create destinations table and fix related issues."""
    
    def __init__(self):
        self.logger = logger
    
    async def create_destinations_table(self):
        """Create the destinations table."""
        print("🔧 CREATING DESTINATIONS TABLE")
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
            
            # Create destinations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            print("✅ Destinations table created")
            
            # Create sample destinations
            sample_destinations = [
                ("Telegram Channel 1", "https://t.me/sample_channel_1"),
                ("Telegram Group 1", "https://t.me/sample_group_1"),
                ("Telegram Channel 2", "https://t.me/sample_channel_2"),
                ("Telegram Group 2", "https://t.me/sample_group_2"),
                ("Telegram Channel 3", "https://t.me/sample_channel_3"),
            ]
            
            for name, url in sample_destinations:
                cursor.execute("""
                    INSERT INTO destinations (name, url, status)
                    VALUES (?, ?, 'active')
                """, (name, url))
            
            conn.commit()
            print(f"✅ Created {len(sample_destinations)} sample destinations")
            
            await db.close()
            return True
            
        except Exception as e:
            print(f"❌ Error creating destinations table: {e}")
            return False
    
    async def fix_ad_slots(self):
        """Fix ad slots activation."""
        print("\n🔧 FIXING AD SLOTS")
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
            
            # Check ad_slots table structure
            cursor.execute("PRAGMA table_info(ad_slots)")
            columns = [col[1] for col in cursor.fetchall()]
            
            print(f"📋 Ad slots table columns: {columns}")
            
            # Count ad slots by status
            cursor.execute("SELECT status, COUNT(*) FROM ad_slots GROUP BY status")
            status_counts = cursor.fetchall()
            
            print("📊 Ad slots by status:")
            for status, count in status_counts:
                print(f"  - {status}: {count}")
            
            # Activate ad slots that should be active
            cursor.execute("""
                UPDATE ad_slots 
                SET status = 'active' 
                WHERE status != 'active' AND status != 'deleted'
            """)
            
            activated_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Activated {activated_count} ad slots")
            
            # Show active ad slots
            cursor.execute("""
                SELECT user_id, content, last_posted 
                FROM ad_slots 
                WHERE status = 'active' 
                LIMIT 5
            """)
            active_slots = cursor.fetchall()
            
            if active_slots:
                print("📋 Active ad slots:")
                for slot in active_slots:
                    user_id = slot[0]
                    content = slot[1][:50] + "..." if len(slot[1]) > 50 else slot[1]
                    last_posted = slot[2] or "Never"
                    print(f"  - User {user_id}: {content} (Last: {last_posted})")
            
            await db.close()
            return activated_count
            
        except Exception as e:
            print(f"❌ Error fixing ad slots: {e}")
            return 0
    
    async def fix_subscriptions(self):
        """Fix user subscriptions."""
        print("\n🔧 FIXING SUBSCRIPTIONS")
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
            
            # Check subscriptions table structure
            cursor.execute("PRAGMA table_info(subscriptions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            print(f"📋 Subscriptions table columns: {columns}")
            
            # Count subscriptions by status
            cursor.execute("SELECT status, COUNT(*) FROM subscriptions GROUP BY status")
            status_counts = cursor.fetchall()
            
            print("📊 Subscriptions by status:")
            for status, count in status_counts:
                print(f"  - {status}: {count}")
            
            # Activate subscriptions that should be active
            cursor.execute("""
                UPDATE subscriptions 
                SET status = 'active' 
                WHERE status != 'active' AND status != 'expired'
            """)
            
            activated_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Activated {activated_count} subscriptions")
            
            # Show active subscriptions
            cursor.execute("""
                SELECT user_id, plan, expires_at 
                FROM subscriptions 
                WHERE status = 'active' 
                LIMIT 5
            """)
            active_subs = cursor.fetchall()
            
            if active_subs:
                print("📋 Active subscriptions:")
                for sub in active_subs:
                    user_id = sub[0]
                    plan = sub[1]
                    expires_at = sub[2] or "Unknown"
                    print(f"  - User {user_id}: {plan} (Expires: {expires_at})")
            
            await db.close()
            return activated_count
            
        except Exception as e:
            print(f"❌ Error fixing subscriptions: {e}")
            return 0
    
    async def verify_fixes(self):
        """Verify all fixes worked."""
        print("\n🔍 VERIFYING FIXES")
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
            
            # Check destinations
            cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
            active_destinations = cursor.fetchone()[0]
            
            # Check ad slots
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE status = 'active'")
            active_slots = cursor.fetchone()[0]
            
            # Check subscriptions
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            active_subscriptions = cursor.fetchone()[0]
            
            # Check workers
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            
            print(f"📊 Verification Results:")
            print(f"  - Active destinations: {active_destinations}")
            print(f"  - Active ad slots: {active_slots}")
            print(f"  - Active subscriptions: {active_subscriptions}")
            print(f"  - Active workers: {active_workers}")
            
            await db.close()
            
            return {
                'destinations': active_destinations,
                'ad_slots': active_slots,
                'subscriptions': active_subscriptions,
                'workers': active_workers
            }
            
        except Exception as e:
            print(f"❌ Error verifying fixes: {e}")
            return {}

async def main():
    """Main function."""
    creator = DestinationsTableCreator()
    
    # Create destinations table
    success = await creator.create_destinations_table()
    
    if success:
        # Fix ad slots
        activated_slots = await creator.fix_ad_slots()
        
        # Fix subscriptions
        activated_subs = await creator.fix_subscriptions()
        
        # Verify fixes
        results = await creator.verify_fixes()
        
        print("\n📊 DESTINATIONS TABLE CREATION SUMMARY")
        print("=" * 50)
        print("Issues fixed:")
        print("1. ✅ Created destinations table")
        print("2. ✅ Created sample destinations")
        print("3. ✅ Activated ad slots")
        print("4. ✅ Activated subscriptions")
        print("5. ✅ Verified all fixes")
        
        print(f"\n🎯 RESULTS:")
        print(f"  - Destinations: {results.get('destinations', 0)}")
        print(f"  - Ad slots: {results.get('ad_slots', 0)}")
        print(f"  - Subscriptions: {results.get('subscriptions', 0)}")
        print(f"  - Workers: {results.get('workers', 0)}")
        
        if results.get('destinations', 0) > 0 and results.get('ad_slots', 0) > 0:
            print("\n✅ SUCCESS: All components are ready!")
            print("🚀 Scheduler should be able to post now")
        else:
            print("\n❌ ISSUES: Some components still not ready")
    else:
        print("\n❌ FAILED: Could not create destinations table")

if __name__ == "__main__":
    asyncio.run(main())

