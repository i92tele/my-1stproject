#!/usr/bin/env python3
"""
Fix Subscription
Create an active subscription for the user so the scheduler can work
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
    print("🔧 FIXING SUBSCRIPTION")
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
        
        # Check current subscriptions
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active_subs = cursor.fetchone()[0]
        
        print(f"📊 Current active subscriptions: {active_subs}")
        
        if active_subs == 0:
            # Get the user from the active ad slot
            cursor.execute("SELECT user_id FROM ad_slots WHERE is_active = 1 LIMIT 1")
            user_result = cursor.fetchone()
            
            if user_result:
                user_id = user_result[0]
                print(f"🔧 Creating subscription for user {user_id}...")
                
                # Create active subscription
                cursor.execute("""
                    INSERT INTO subscriptions (
                        user_id, tier, status, created_at, expires_at
                    ) VALUES (?, 'premium', 'active', CURRENT_TIMESTAMP, 
                    datetime('now', '+30 days'))
                """, (user_id,))
                
                conn.commit()
                print(f"✅ Created active subscription for user {user_id}")
            else:
                print("❌ No active ad slots found")
        else:
            print("✅ Active subscription already exists")
        
        # Final check
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        final_subs = cursor.fetchone()[0]
        
        print(f"\n📊 Final active subscriptions: {final_subs}")
        
        if final_subs > 0:
            print("✅ SUBSCRIPTION FIXED!")
            print("🚀 Scheduler should now work properly")
        else:
            print("❌ Still no active subscriptions")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
