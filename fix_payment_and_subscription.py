#!/usr/bin/env python3
"""
Fix payment status and activate subscription manually.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_payment_and_subscription():
    """Fix the payment status and activate subscription."""
    print("🔧 FIXING PAYMENT AND SUBSCRIPTION")
    print("=" * 50)
    
    try:
        # Initialize database
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        payment_id = "TON_67f36980c5bf4afe"
        user_id = 7593457389
        
        print(f"1️⃣ Checking payment {payment_id}...")
        
        # Get current payment status
        payment = await db.get_payment(payment_id)
        if not payment:
            print(f"❌ Payment {payment_id} not found")
            return
        
        print(f"   Current status: {payment['status']}")
        print(f"   User ID: {payment['user_id']}")
        print(f"   Amount: {payment.get('amount_usd', 'N/A')} USD")
        
        # Update payment status to completed
        print(f"\n2️⃣ Updating payment status to 'completed'...")
        success = await db.update_payment_status(payment_id, 'completed')
        if success:
            print(f"✅ Payment status updated to 'completed'")
        else:
            print(f"❌ Failed to update payment status")
            return
        
        # Check user subscription
        print(f"\n3️⃣ Checking user subscription...")
        user = await db.get_user(user_id)
        if not user:
            print(f"❌ User {user_id} not found")
            return
        
        print(f"   Current tier: {user.get('subscription_tier', 'None')}")
        print(f"   Current expires: {user.get('subscription_expires', 'None')}")
        
        # Activate subscription
        print(f"\n4️⃣ Activating subscription...")
        success = await db.activate_subscription(user_id, 'basic', 30)
        if success:
            print(f"✅ Subscription activated successfully")
        else:
            print(f"❌ Failed to activate subscription")
            return
        
        # Verify the changes
        print(f"\n5️⃣ Verifying changes...")
        
        # Check payment status
        payment_after = await db.get_payment(payment_id)
        print(f"   Payment status: {payment_after['status']}")
        
        # Check subscription
        user_after = await db.get_user(user_id)
        print(f"   Subscription tier: {user_after.get('subscription_tier', 'None')}")
        print(f"   Subscription expires: {user_after.get('subscription_expires', 'None')}")
        
        if user_after.get('subscription_tier') == 'basic' and user_after.get('subscription_expires'):
            print(f"\n🎉 SUCCESS! Subscription is now active!")
            print(f"   Tier: {user_after.get('subscription_tier')}")
            print(f"   Expires: {user_after.get('subscription_expires')}")
        else:
            print(f"\n❌ Subscription activation failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_payment_and_subscription())
