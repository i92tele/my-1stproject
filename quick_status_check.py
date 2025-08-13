#!/usr/bin/env python3
"""
Quick Status Check Script
Checks current system state without terminal dependency
"""

import asyncio
import logging
import json
from datetime import datetime
from database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_system_status():
    """Check current system status."""
    print("🔍 Quick System Status Check")
    print("=" * 50)
    
    try:
        # Initialize database
        db = DatabaseManager('bot_database.db', logger)
        await db.initialize()
        
        # Check user subscription
        user_id = 7172873873
        subscription = await db.get_user_subscription(user_id)
        
        print(f"📊 User {user_id} Status:")
        if subscription:
            print(f"  ✅ Subscription: {subscription.get('tier', 'none')}")
            print(f"  📅 Expires: {subscription.get('subscription_expires', 'unknown')}")
        else:
            print("  ❌ No subscription found")
        
        # Check ad slots
        slots = await db.get_or_create_ad_slots(user_id, subscription.get('tier', 'basic') if subscription else 'basic')
        print(f"  📦 Ad Slots: {len(slots)}")
        
        # Check active slots
        active_slots = await db.get_active_ad_slots()
        print(f"  🚀 Active Slots: {len(active_slots)}")
        
        # Check destinations
        total_destinations = 0
        for slot in slots:
            slot_destinations = await db.get_destinations_for_slot(slot.get('id'))
            total_destinations += len(slot_destinations) if slot_destinations else 0
        
        print(f"  📍 Total Destinations: {total_destinations}")
        
        # Check managed groups
        groups = await db.get_managed_groups()
        print(f"  👥 Managed Groups: {len(groups)}")
        
        # Check active ads to send
        active_ads = await db.get_active_ads_to_send()
        print(f"  📝 Active Ads to Send: {len(active_ads)}")
        
        print("\n✅ System Status Check Complete")
        
        # Save results to file
        results = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "subscription": subscription.get('tier') if subscription else None,
            "total_slots": len(slots),
            "active_slots": len(active_slots),
            "total_destinations": total_destinations,
            "managed_groups": len(groups),
            "active_ads_to_send": len(active_ads)
        }
        
        with open('status_check_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("📄 Results saved to: status_check_results.json")
        
    except Exception as e:
        print(f"❌ Error during status check: {e}")
        logger.error(f"Status check error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_system_status())
