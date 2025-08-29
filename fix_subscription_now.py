#!/usr/bin/env python3
"""
Fix subscription activation with proper date calculation
"""

import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

async def fix_subscription_activation():
    """Fix subscription activation for the recent payment."""
    print("🔧 Fixing Subscription Activation...")
    
    db_path = "bot_database.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check the recent payment
        print(f"\n1️⃣ Checking payment TON_203ab0aa0997420d...")
        cursor.execute('''
            SELECT payment_id, user_id, amount_usd, crypto_type, status 
            FROM payments 
            WHERE payment_id = 'TON_203ab0aa0997420d'
        ''')
        payment = cursor.fetchone()
        
        if payment:
            payment_id, user_id, amount_usd, crypto_type, status = payment
            print(f"✅ Payment found: User {user_id}, Amount ${amount_usd}, Status {status}")
        else:
            print(f"❌ Payment not found")
            return
        
        # Check current user subscription
        print(f"\n2️⃣ Checking current subscription...")
        cursor.execute('''
            SELECT subscription_tier, subscription_expires 
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if user:
            subscription_tier, subscription_expires = user
            print(f"   Current Tier: {subscription_tier}")
            print(f"   Current Expires: {subscription_expires}")
            
            if subscription_tier and subscription_expires:
                print("✅ Subscription already exists")
                return
            else:
                print("❌ No subscription found, will activate...")
        else:
            print(f"❌ User not found")
            return
        
        # Activate subscription
        print(f"\n3️⃣ Activating subscription...")
        
        # Determine tier from payment amount
        if amount_usd >= 75:
            tier = 'enterprise'
        elif amount_usd >= 45:
            tier = 'pro'
        else:
            tier = 'basic'
        
        # Calculate expiry date (30 days from now)
        new_expiry = datetime.now() + timedelta(days=30)
        new_expiry_str = new_expiry.isoformat()
        
        print(f"   Tier: {tier}")
        print(f"   Expires: {new_expiry_str}")
        
        # Update user subscription
        cursor.execute('''
            UPDATE users 
            SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
            WHERE user_id = ?
        ''', (tier, new_expiry_str, datetime.now().isoformat(), user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ Subscription activated successfully!")
        else:
            print(f"❌ Failed to activate subscription")
            return
        
        # Verify activation
        print(f"\n4️⃣ Verifying activation...")
        cursor.execute('''
            SELECT subscription_tier, subscription_expires 
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        final_user = cursor.fetchone()
        
        if final_user:
            subscription_tier, subscription_expires = final_user
            if subscription_tier and subscription_expires:
                expires_date = datetime.fromisoformat(subscription_expires)
                is_active = expires_date > datetime.now()
                print(f"✅ Final status: Tier={subscription_tier}, Expires={subscription_expires}")
                print(f"   Is Active: {is_active}")
                
                if is_active:
                    print("🎉 SUBSCRIPTION IS NOW ACTIVE!")
                else:
                    print("⚠️ Subscription exists but is not active")
            else:
                print("❌ Still no subscription found")
        
        conn.close()
        print(f"\n✅ Subscription activation completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_subscription_activation())
