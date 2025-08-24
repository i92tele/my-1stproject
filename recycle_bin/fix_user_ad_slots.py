#!/usr/bin/env python3
"""
Fix User Ad Slots
Check and fix a user's ad slots based on their subscription tier
"""

import asyncio
import logging
from src.database.manager import DatabaseManager
from config import BotConfig

async def fix_user_ad_slots(user_id: int):
    """Check and fix a user's ad slots based on their subscription tier"""
    print(f"🔧 Fixing ad slots for user {user_id}")
    print("=" * 50)
    
    try:
        # Initialize components
        config = BotConfig()
        logger = logging.getLogger(__name__)
        db_manager = DatabaseManager('bot_database.db', logger)
        await db_manager.initialize()
        
        # Get user subscription
        subscription = await db_manager.get_user_subscription(user_id)
        if not subscription:
            print(f"❌ User {user_id} has no active subscription")
            return False
        
        tier = subscription.get('tier', 'basic')
        print(f"📋 User subscription: {tier}")
        
        # Get current ad slots
        current_slots = await db_manager.get_user_ad_slots(user_id)
        print(f"📢 Current ad slots: {len(current_slots)}")
        
        # Show current slots
        for slot in current_slots:
            print(f"  - Slot {slot.get('slot_number')}: {slot.get('is_active', 0)}")
        
        # Fix ad slots based on tier
        print(f"\n🔧 Fixing ad slots for tier: {tier}")
        fixed_slots = await db_manager.get_or_create_ad_slots(user_id, tier)
        
        print(f"✅ Fixed ad slots: {len(fixed_slots)}")
        for slot in fixed_slots:
            print(f"  - Slot {slot.get('slot_number')}: {slot.get('is_active', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main function"""
    print("🔧 User Ad Slots Fixer")
    print("=" * 30)
    
    # You can change this user ID to fix a specific user
    user_id = int(input("Enter user ID to fix: "))
    
    success = await fix_user_ad_slots(user_id)
    if success:
        print("\n✅ Ad slots fixed successfully!")
    else:
        print("\n❌ Failed to fix ad slots")

if __name__ == "__main__":
    asyncio.run(main())
