#!/usr/bin/env python3
"""
Check subscription status and fix any issues
"""

import asyncio
import sqlite3
import os
from datetime import datetime

async def check_and_fix_subscription():
    """Check subscription status and fix any issues."""
    print("🔍 Checking Subscription Status...")
    
    db_path = "bot_database.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check the recent payment
        print(f"\n1️⃣ Checking recent payment...")
        cursor.execute('''
            SELECT payment_id, user_id, amount_usd, crypto_type, status, created_at, updated_at 
            FROM payments 
            WHERE payment_id = 'TON_203ab0aa0997420d'
        ''')
        payment = cursor.fetchone()
        
        if payment:
            print(f"✅ Payment found: {payment}")
            payment_id, user_id, amount_usd, crypto_type, status, created_at, updated_at = payment
            print(f"   User ID: {user_id}")
            print(f"   Status: {status}")
            print(f"   Amount: ${amount_usd}")
            print(f"   Crypto: {crypto_type}")
        else:
            print(f"❌ Payment not found in database")
            return
        
        # Check user subscription
        print(f"\n2️⃣ Checking user subscription...")
        cursor.execute('''
            SELECT user_id, username, subscription_tier, subscription_expires, updated_at 
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ User found: {user}")
            user_id, username, subscription_tier, subscription_expires, updated_at = user
            print(f"   Username: {username}")
            print(f"   Subscription Tier: {subscription_tier}")
            print(f"   Subscription Expires: {subscription_expires}")
            
            if subscription_tier and subscription_expires:
                expires_date = datetime.fromisoformat(subscription_expires)
                is_active = expires_date > datetime.now()
                print(f"   Is Active: {is_active}")
                
                if is_active:
                    print("🎉 Subscription is ACTIVE!")
                else:
                    print("⚠️ Subscription has EXPIRED")
            else:
                print("❌ No subscription found")
        else:
            print(f"❌ User not found")
            return
        
        # Check if payment status needs updating
        print(f"\n3️⃣ Checking payment status...")
        if status != 'completed':
            print(f"⚠️ Payment status is '{status}', updating to 'completed'...")
            cursor.execute('''
                UPDATE payments 
                SET status = 'completed', updated_at = ? 
                WHERE payment_id = ?
            ''', (datetime.now().isoformat(), payment_id))
            conn.commit()
            print(f"✅ Payment status updated to 'completed'")
        else:
            print(f"✅ Payment status is already 'completed'")
        
        # Check if subscription needs activation
        print(f"\n4️⃣ Checking if subscription needs activation...")
        if not subscription_tier or not subscription_expires:
            print(f"⚠️ No subscription found, activating...")
            
            # Determine tier from payment amount
            if amount_usd >= 75:
                tier = 'enterprise'
            elif amount_usd >= 45:
                tier = 'pro'
            else:
                tier = 'basic'
            
            # Calculate expiry date
            new_expiry = datetime.now().replace(microsecond=0) + asyncio.get_event_loop().time() + 30 * 24 * 3600
            new_expiry_str = new_expiry.isoformat()
            
            # Activate subscription
            cursor.execute('''
                UPDATE users 
                SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
                WHERE user_id = ?
            ''', (tier, new_expiry_str, datetime.now().isoformat(), user_id))
            conn.commit()
            
            print(f"✅ Subscription activated!")
            print(f"   Tier: {tier}")
            print(f"   Expires: {new_expiry_str}")
        else:
            print(f"✅ Subscription already exists")
        
        # Final verification
        print(f"\n5️⃣ Final verification...")
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
                print(f"✅ Final status: Tier={subscription_tier}, Expires={subscription_expires}, Active={is_active}")
                
                if is_active:
                    print("🎉 SUBSCRIPTION IS NOW ACTIVE!")
                else:
                    print("⚠️ Subscription exists but is not active")
            else:
                print("❌ Still no subscription found")
        
        conn.close()
        print(f"\n✅ Check and fix completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_and_fix_subscription())
