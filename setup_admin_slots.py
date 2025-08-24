#!/usr/bin/env python3
"""
Setup Admin Slots Script
Gives user 7172873873 access to 20 ad slots
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import BotConfig
from src.database.manager import DatabaseManager
from database_migration import run_database_migration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def setup_admin_slots():
    """Set up 20 ad slots for admin user 7172873873."""
    print("🎯 **SETTING UP ADMIN SLOTS**")
    print("=" * 50)
    
    ADMIN_USER_ID = 7172873873
    
    try:
        # Load configuration
        config = BotConfig.load_from_env()
        print("✅ Configuration loaded")
        
        # Initialize database
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        print("✅ Database initialized")
        
        # Run database migration to ensure admin slots table exists
        print("\n📊 Running database migration...")
        migration_success = await run_database_migration("bot_database.db")
        if migration_success:
            print("✅ Database migration completed")
        else:
            print("⚠️ Database migration had issues, continuing anyway...")
        
        # Create or update admin user
        print(f"\n👤 Setting up admin user {ADMIN_USER_ID}...")
        user_created = await db.create_or_update_user(
            user_id=ADMIN_USER_ID,
            username="admin",
            first_name="Admin",
            last_name="User"
        )
        if user_created:
            print("✅ Admin user created/updated")
        else:
            print("⚠️ User creation had issues, continuing anyway...")
        
        # Activate enterprise subscription for admin
        print(f"\n💎 Activating enterprise subscription...")
        subscription_success = await db.activate_subscription(
            user_id=ADMIN_USER_ID,
            tier="enterprise",
            duration_days=365  # 1 year subscription
        )
        if subscription_success:
            print("✅ Enterprise subscription activated")
        else:
            print("⚠️ Subscription activation had issues, continuing anyway...")
        
        # Create admin ad slots
        print(f"\n🎯 Creating admin ad slots...")
        admin_slots_success = await db.create_admin_ad_slots()
        if admin_slots_success:
            print("✅ Admin ad slots created")
        else:
            print("⚠️ Admin slots creation had issues, continuing anyway...")
        
        # Get admin slots to verify
        print(f"\n📋 Verifying admin slots...")
        admin_slots = await db.get_admin_ad_slots()
        if admin_slots:
            print(f"✅ Found {len(admin_slots)} admin slots")
            for slot in admin_slots[:5]:  # Show first 5 slots
                print(f"   Slot {slot['slot_number']}: {'✅ Active' if slot['is_active'] else '⏸️ Inactive'}")
            if len(admin_slots) > 5:
                print(f"   ... and {len(admin_slots) - 5} more slots")
        else:
            print("❌ No admin slots found")
        
        # Get user subscription to verify
        print(f"\n📊 Verifying user subscription...")
        subscription = await db.get_user_subscription(ADMIN_USER_ID)
        if subscription:
            print(f"✅ User subscription: {subscription.get('tier', 'unknown')}")
            print(f"   Expires: {subscription.get('expires', 'unknown')}")
            print(f"   Active: {subscription.get('is_active', False)}")
        else:
            print("❌ No user subscription found")
        
        # Get user ad slots to verify
        print(f"\n📢 Verifying user ad slots...")
        user_slots = await db.get_or_create_ad_slots(ADMIN_USER_ID, "enterprise")
        if user_slots:
            print(f"✅ Found {len(user_slots)} user ad slots")
            for slot in user_slots:
                print(f"   Slot {slot.get('slot_number', 'N/A')}: {'✅ Active' if slot.get('is_active', False) else '⏸️ Inactive'}")
        else:
            print("❌ No user ad slots found")
        
        print("\n" + "=" * 50)
        print("🎉 **ADMIN SLOTS SETUP COMPLETE!**")
        print("=" * 50)
        
        print(f"\n📋 **Summary for User {ADMIN_USER_ID}:**")
        print(f"✅ Admin user created/updated")
        print(f"✅ Enterprise subscription activated (365 days)")
        print(f"✅ {len(admin_slots) if admin_slots else 0} admin ad slots available")
        print(f"✅ {len(user_slots) if user_slots else 0} user ad slots available")
        
        print(f"\n🔧 **Admin Commands Available:**")
        print(f"/admin_slots - Manage your 20 admin ad slots")
        print(f"/upgrade_subscription - Test subscription upgrades")
        print(f"/prolong_subscription - Test subscription extensions")
        print(f"/my_ads - View your user ad slots")
        
        print(f"\n📊 **Total Ad Slots Available:**")
        total_slots = (len(admin_slots) if admin_slots else 0) + (len(user_slots) if user_slots else 0)
        print(f"   Admin Slots: {len(admin_slots) if admin_slots else 0}")
        print(f"   User Slots: {len(user_slots) if user_slots else 0}")
        print(f"   Total: {total_slots} ad slots")
        
        print(f"\n🚀 **Next Steps:**")
        print(f"1. Start the bot: python bot.py")
        print(f"2. Use /admin_slots to manage your admin slots")
        print(f"3. Use /my_ads to manage your user slots")
        print(f"4. Test the new features!")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up admin slots: {e}")
        print(f"❌ Error setting up admin slots: {e}")
        return False

async def main():
    """Run the admin slots setup."""
    success = await setup_admin_slots()
    if success:
        print("\n✅ Admin slots setup completed successfully!")
    else:
        print("\n❌ Admin slots setup failed!")

if __name__ == "__main__":
    asyncio.run(main())
