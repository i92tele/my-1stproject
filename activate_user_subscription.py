#!/usr/bin/env python3
"""
Manually activate subscription for user 7593457389
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.manager import DatabaseManager
from src.config.bot_config import BotConfig

async def activate_user_subscription():
    """Activate subscription for user 7593457389."""
    print("🎯 Activating subscription for user 7593457389...")
    
    # Initialize database with proper logger
    config = BotConfig.load_from_env()
    logger = logging.getLogger(__name__)
    db = DatabaseManager("bot_database.db", logger)
    await db.initialize()
    
    user_id = 7593457389
    
    try:
        # Step 1: Check if user already exists in database
        print(f"1️⃣ Checking if user {user_id} exists in database...")
        conn = await db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name FROM users WHERE user_id = ?', (user_id,))
        existing_user = cursor.fetchone()
        conn.close()
        
        if existing_user:
            print(f"✅ User already exists: ID={existing_user[0]}, Username={existing_user[1]}, Name={existing_user[2]}")
            username = existing_user[1] or f"user_{user_id}"
            first_name = existing_user[2] or "User"
        else:
            print(f"❌ User not found in database, will create new user")
            username = f"user_{user_id}"
            first_name = "User"
        
        # Step 2: Create user if doesn't exist
        print(f"2️⃣ Ensuring user {user_id} exists...")
        user_created = await db.create_user(user_id, username, first_name)
        print(f"✅ User creation: {user_created}")
        
        # Step 3: Activate basic subscription
        print(f"3️⃣ Activating basic subscription...")
        activation_result = await db.activate_subscription(user_id, "basic", 30)
        print(f"✅ Activation result: {activation_result}")
        
        # Step 4: Verify subscription
        print(f"4️⃣ Verifying subscription...")
        subscription = await db.get_user_subscription(user_id)
        if subscription and subscription['is_active']:
            print(f"🎉 SUCCESS! User {user_id} now has active subscription:")
            print(f"   Tier: {subscription['tier']}")
            print(f"   Expires: {subscription['expires']}")
            print(f"   Active: {subscription['is_active']}")
        else:
            print(f"❌ FAILED! Subscription not active: {subscription}")
        
        # Step 5: Check payment status
        print(f"5️⃣ Checking payment status...")
        payment = await db.get_payment("TON_d242ac8a83e64a70")
        if payment:
            print(f"✅ Payment found: {payment['status']}")
            if payment['status'] != 'completed':
                print(f"   Updating payment status to completed...")
                await db.update_payment_status("TON_d242ac8a83e64a70", "completed")
                print(f"   ✅ Payment status updated")
        else:
            print(f"❌ Payment not found")
        
        # Step 6: Final verification
        print(f"6️⃣ Final verification...")
        final_subscription = await db.get_user_subscription(user_id)
        if final_subscription and final_subscription['is_active']:
            print(f"🎉 COMPLETE! User {user_id} subscription is now active and ready to use!")
        else:
            print(f"❌ ISSUE: Subscription still not active")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(activate_user_subscription())
