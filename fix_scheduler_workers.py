#!/usr/bin/env python3
"""
Fix Scheduler Workers
Quick fix to ensure workers are properly counted by the scheduler
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
    print("🔧 FIXING SCHEDULER WORKERS")
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
        
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
        active_destinations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        active_slots = cursor.fetchone()[0]
        
        print(f"📊 Current Status:")
        print(f"  - Active workers: {active_workers}")
        print(f"  - Active destinations: {active_destinations}")
        print(f"  - Active ad slots: {active_slots}")
        
        # Ensure all workers are active
        if active_workers == 0:
            print("🔧 Activating all workers...")
            cursor.execute("UPDATE workers SET is_active = 1")
            conn.commit()
            print("✅ All workers activated")
        
        # Ensure destinations are active
        if active_destinations == 0:
            print("🔧 Activating destinations...")
            cursor.execute("UPDATE destinations SET status = 'active'")
            conn.commit()
            print("✅ All destinations activated")
        
        # Final check
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        final_workers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
        final_destinations = cursor.fetchone()[0]
        
        print(f"\n📊 Final Status:")
        print(f"  - Active workers: {final_workers}")
        print(f"  - Active destinations: {final_destinations}")
        print(f"  - Active ad slots: {active_slots}")
        
        if final_workers > 0 and final_destinations > 0 and active_slots > 0:
            print("\n✅ SCHEDULER READY!")
            print("🚀 The bot should now be able to post ads")
        else:
            print("\n❌ Still missing components")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
