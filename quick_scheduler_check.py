#!/usr/bin/env python3
"""
Quick Scheduler Check
Quick check of scheduler status and posting activity
"""

import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def quick_scheduler_check():
    """Quick check of scheduler status."""
    print("📅 QUICK SCHEDULER CHECK")
    print("=" * 40)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        print("✅ Database connected")
        
        # Check active workers
        workers = await db.get_all_workers()
        active_workers = len([w for w in workers if w.get('status') == 'active'])
        print(f"👥 Active workers: {active_workers}")
        
        # Check active ad slots
        ad_slots = await db.get_ad_slots()
        active_slots = len([s for s in ad_slots if s.get('is_active')])
        print(f"📝 Active ad slots: {active_slots}")
        
        # Check active destinations
        destinations = await db.get_destinations()
        active_destinations = len([d for d in destinations if d.get('is_active')])
        print(f"🎯 Active destinations: {active_destinations}")
        
        # Check recent posting activity
        recent_posts = await db.get_recent_posting_activity(hours=24)
        
        if recent_posts:
            print(f"📊 Recent posting activity:")
            for post in recent_posts:
                print(f"  - Slot {post[0]}: Last posted {post[1]}, Next post {post[2]}")
        else:
            print("⚠️ No recent posting activity found")
        
        # Check scheduler log for recent activity
        log_file = "scheduler.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-5:] if len(lines) > 5 else lines
            
            print(f"📋 Recent scheduler activity:")
            for line in recent_lines:
                if line.strip():
                    print(f"  - {line.strip()}")
        
        await db.close()
        
        # Overall assessment
        print(f"\n📊 SCHEDULER ASSESSMENT:")
        if active_workers > 0 and active_slots > 0 and active_destinations > 0:
            print("✅ Scheduler should be operational")
            print("✅ Workers available for posting")
            print("✅ Active slots to post")
            print("✅ Destinations configured")
        elif active_workers == 0:
            print("❌ No active workers - scheduler cannot post")
        elif active_slots == 0:
            print("⚠️ No active ad slots - nothing to post")
        elif active_destinations == 0:
            print("❌ No active destinations - nowhere to post")
        else:
            print("⚠️ Mixed status - some components missing")
        
    except Exception as e:
        print(f"❌ Error checking scheduler: {e}")

async def main():
    """Main function."""
    await quick_scheduler_check()

if __name__ == "__main__":
    asyncio.run(main())
