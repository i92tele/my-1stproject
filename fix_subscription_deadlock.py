#!/usr/bin/env python3
"""
Fix subscription activation deadlock
"""

import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

async def fix_subscription_activation():
    """Fix the subscription activation for user 7593457389."""
    print("🔧 Fixing Subscription Activation Deadlock...")
    
    user_id = 7593457389
    db_path = "bot_database.db"
    
    try:
        # Direct database access to avoid deadlock
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current user state
        print(f"\n1️⃣ Checking current user state...")
        cursor.execute('SELECT user_id, username, subscription_tier, subscription_expires FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ User found: {user}")
        else:
            print(f"❌ User not found")
            return
        
        # Check if subscription needs activation
        subscription_tier = user[2]
        subscription_expires = user[3]
        
        if subscription_tier and subscription_expires:
            expires_date = datetime.fromisoformat(subscription_expires)
            is_active = expires_date > datetime.now()
            print(f"📅 Current subscription: Tier={subscription_tier}, Expires={subscription_expires}, Active={is_active}")
            
            if is_active:
                print("✅ Subscription is already active!")
                return
            else:
                print("⚠️ Subscription has expired, will extend it")
        else:
            print("❌ No subscription found, will create new one")
        
        # Activate subscription directly in database
        print(f"\n2️⃣ Activating subscription directly...")
        
        # Calculate new expiry date
        new_expiry = datetime.now() + timedelta(days=30)
        new_expiry_str = new_expiry.isoformat()
        
        # Update subscription
        cursor.execute('''
            UPDATE users 
            SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
            WHERE user_id = ?
        ''', ('basic', new_expiry_str, datetime.now().isoformat(), user_id))
        
        if cursor.rowcount > 0:
            print(f"✅ Subscription activated successfully!")
            print(f"   Tier: basic")
            print(f"   Expires: {new_expiry_str}")
        else:
            print(f"❌ Failed to activate subscription")
            return
        
        # Commit changes
        conn.commit()
        
        # Verify the activation
        print(f"\n3️⃣ Verifying activation...")
        cursor.execute('SELECT subscription_tier, subscription_expires FROM users WHERE user_id = ?', (user_id,))
        updated_user = cursor.fetchone()
        
        if updated_user and updated_user[0] == 'basic':
            print(f"✅ Verification successful!")
            print(f"   Tier: {updated_user[0]}")
            print(f"   Expires: {updated_user[1]}")
            
            # Check if active
            expires_date = datetime.fromisoformat(updated_user[1])
            is_active = expires_date > datetime.now()
            print(f"   Is Active: {is_active}")
            
            if is_active:
                print("🎉 SUBSCRIPTION IS NOW ACTIVE!")
            else:
                print("⚠️ Subscription exists but is not active")
        else:
            print(f"❌ Verification failed: {updated_user}")
        
        # Check payment status
        print(f"\n4️⃣ Checking payment status...")
        cursor.execute('SELECT payment_id, status FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user_id,))
        payment = cursor.fetchone()
        
        if payment:
            print(f"✅ Payment found: {payment[0]} - Status: {payment[1]}")
            if payment[1] != 'completed':
                print(f"   Updating payment status to completed...")
                cursor.execute('UPDATE payments SET status = ? WHERE payment_id = ?', ('completed', payment[0]))
                conn.commit()
                print(f"   ✅ Payment status updated to completed")
        else:
            print(f"❌ No payment found for user")
        
        conn.close()
        print(f"\n✅ Subscription activation fix completed!")
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_subscription_activation())
