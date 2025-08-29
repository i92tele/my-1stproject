#!/usr/bin/env python3
"""
Fix the current payment and activate subscription.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_payment_now():
    """Fix the current payment directly in the database."""
    print("🔧 FIXING PAYMENT NOW")
    print("=" * 50)
    
    # Initialize database
    db = DatabaseManager("bot_database.db", logger)
    await db.initialize()
    
    payment_id = "TON_1b3c694be76547ad"
    user_id = 7593457389
    
    # 1. Mark payment as completed
    print(f"1. Marking payment {payment_id} as completed...")
    await db.update_payment_status(payment_id, 'completed')
    
    # 2. Activate subscription directly
    print(f"2. Activating subscription for user {user_id}...")
    expiry = datetime.now() + timedelta(days=30)
    
    # Connect to database directly
    conn = await db.get_connection()
    cursor = conn.cursor()
    
    # Update subscription in users table
    cursor.execute('''
        UPDATE users 
        SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
        WHERE user_id = ?
    ''', ('basic', expiry.isoformat(), datetime.now().isoformat(), user_id))
    
    conn.commit()
    
    # 3. Verify changes
    print(f"3. Verifying changes...")
    
    # Check payment status
    cursor.execute('SELECT status FROM payments WHERE payment_id = ?', (payment_id,))
    payment_status = cursor.fetchone()[0]
    print(f"   Payment status: {payment_status}")
    
    # Check subscription
    cursor.execute('SELECT subscription_tier, subscription_expires FROM users WHERE user_id = ?', (user_id,))
    subscription = cursor.fetchone()
    if subscription:
        tier, expires = subscription
        print(f"   Subscription tier: {tier}")
        print(f"   Subscription expires: {expires}")
        print(f"   ✅ Subscription activated successfully!")
    else:
        print(f"   ❌ No subscription found")
    
    conn.close()
    await db.close()

if __name__ == "__main__":
    asyncio.run(fix_payment_now())
