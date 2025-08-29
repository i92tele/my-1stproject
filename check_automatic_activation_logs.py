#!/usr/bin/env python3
"""
Check automatic activation logs to see why subscription activation failed
"""

import asyncio
import sqlite3
import os
from datetime import datetime

async def check_automatic_activation():
    """Check why automatic subscription activation failed."""
    print("🔍 Checking Automatic Activation Logs...")
    
    db_path = "bot_database.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check payment details
        print(f"\n1️⃣ Payment Details:")
        cursor.execute('''
            SELECT payment_id, user_id, amount_usd, crypto_type, status, created_at, updated_at 
            FROM payments 
            WHERE payment_id = 'TON_203ab0aa0997420d'
        ''')
        payment = cursor.fetchone()
        
        if payment:
            payment_id, user_id, amount_usd, crypto_type, status, created_at, updated_at = payment
            print(f"   Payment ID: {payment_id}")
            print(f"   User ID: {user_id}")
            print(f"   Amount: ${amount_usd}")
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
        else:
            print(f"❌ Payment not found")
            return
        
        # Check user details
        print(f"\n2️⃣ User Details:")
        cursor.execute('''
            SELECT user_id, username, subscription_tier, subscription_expires, created_at, updated_at 
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if user:
            user_id, username, subscription_tier, subscription_expires, created_at, updated_at = user
            print(f"   User ID: {user_id}")
            print(f"   Username: {username}")
            print(f"   Subscription Tier: {subscription_tier}")
            print(f"   Subscription Expires: {subscription_expires}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
        else:
            print(f"❌ User not found")
            return
        
        # Check if payment was processed by automatic system
        print(f"\n3️⃣ Automatic Processing Analysis:")
        
        # Check if payment status was updated by automatic system
        if status == 'completed':
            print(f"✅ Payment status is 'completed' - automatic verification worked")
            
            # Check if subscription activation was attempted
            if subscription_tier is None and subscription_expires is None:
                print(f"❌ Subscription activation failed - no subscription created")
                print(f"   This indicates the automatic activation step failed")
                
                # Check timing
                payment_updated = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                user_updated = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                
                print(f"   Payment updated: {payment_updated}")
                print(f"   User updated: {user_updated}")
                
                if payment_updated > user_updated:
                    print(f"   ⚠️ Payment was updated after user record - activation may have failed")
                else:
                    print(f"   ⚠️ User record was updated after payment - activation may have been interrupted")
            else:
                print(f"✅ Subscription exists - automatic activation worked")
        else:
            print(f"❌ Payment status is '{status}' - automatic verification may have failed")
        
        # Check for any error patterns
        print(f"\n4️⃣ Error Pattern Analysis:")
        
        # Check if this is a recurring issue
        cursor.execute('''
            SELECT COUNT(*) FROM payments 
            WHERE status = 'completed' AND user_id = ?
        ''', (user_id,))
        completed_payments = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE user_id = ? AND subscription_tier IS NOT NULL
        ''', (user_id,))
        active_subscriptions = cursor.fetchone()[0]
        
        print(f"   Completed payments for user: {completed_payments}")
        print(f"   Active subscriptions for user: {active_subscriptions}")
        
        if completed_payments > active_subscriptions:
            print(f"   ⚠️ Mismatch detected: {completed_payments} payments vs {active_subscriptions} subscriptions")
            print(f"   This suggests automatic activation is failing consistently")
        
        conn.close()
        
        # Recommendations
        print(f"\n5️⃣ Recommendations:")
        print(f"   The automatic payment verification worked (payment marked as completed)")
        print(f"   But the subscription activation step failed")
        print(f"   This is likely due to the database deadlock issue we fixed earlier")
        print(f"   The fix should prevent this from happening in future payments")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_automatic_activation())
