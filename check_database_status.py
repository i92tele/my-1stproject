#!/usr/bin/env python3
"""
Check database status to understand the logic flow.
"""

import sqlite3
import sys
import os
from datetime import datetime

def check_database_status():
    """Check the current database status."""
    print("🔍 Checking database status...")
    
    db_path = "bot_database.db"
    user_id = 7593457389
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n1️⃣ User table status:")
        cursor.execute("""
            SELECT user_id, username, first_name, subscription_tier, subscription_expires, created_at, updated_at
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        if user_data:
            print(f"✅ User found:")
            print(f"   User ID: {user_data[0]}")
            print(f"   Username: {user_data[1]}")
            print(f"   First Name: {user_data[2]}")
            print(f"   Subscription Tier: {user_data[3]}")
            print(f"   Subscription Expires: {user_data[4]}")
            print(f"   Created: {user_data[5]}")
            print(f"   Updated: {user_data[6]}")
            
            # Check if subscription is active
            if user_data[3] and user_data[4]:
                expires_dt = datetime.fromisoformat(user_data[4])
                is_active = expires_dt > datetime.now()
                print(f"   Is Active: {is_active}")
                print(f"   Expires in: {expires_dt - datetime.now()}")
            else:
                print(f"   ❌ No subscription data")
        else:
            print(f"❌ User {user_id} not found in users table")
        
        print(f"\n2️⃣ Payments table status:")
        cursor.execute("""
            SELECT payment_id, status, amount_usd, tier, created_at, updated_at
            FROM payments WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        
        payments = cursor.fetchall()
        if payments:
            print(f"✅ Found {len(payments)} payments:")
            for payment in payments:
                print(f"   Payment ID: {payment[0]}")
                print(f"   Status: {payment[1]}")
                print(f"   Amount: ${payment[2]}")
                print(f"   Tier: {payment[3]}")
                print(f"   Created: {payment[4]}")
                print(f"   Updated: {payment[5]}")
                print(f"   ---")
        else:
            print(f"❌ No payments found for user {user_id}")
        
        print(f"\n3️⃣ Ad slots table status:")
        cursor.execute("""
            SELECT id, slot_number, content, is_active, created_at
            FROM ad_slots WHERE user_id = ? ORDER BY slot_number
        """, (user_id,))
        
        ad_slots = cursor.fetchall()
        if ad_slots:
            print(f"✅ Found {len(ad_slots)} ad slots:")
            for slot in ad_slots:
                print(f"   Slot {slot[1]}: {'Active' if slot[3] else 'Inactive'}")
                print(f"   Content: {slot[2][:50] if slot[2] else 'Empty'}...")
        else:
            print(f"❌ No ad slots found for user {user_id}")
        
        conn.close()
        
        print(f"\n🔍 Logic Flow Analysis:")
        print(f"=" * 50)
        
        if user_data and user_data[3] and user_data[4]:
            print(f"✅ User has subscription data in database")
            if is_active:
                print(f"✅ Subscription is active")
                print(f"✅ The issue was likely the create_or_update_user overwriting subscription")
                print(f"✅ Our fix should resolve this")
            else:
                print(f"❌ Subscription has expired")
                print(f"❌ Need to reactivate subscription")
        elif payments and any(p[1] == 'completed' for p in payments):
            print(f"✅ Found completed payments")
            print(f"❌ But no active subscription")
            print(f"❌ This suggests the payment-to-subscription flow failed")
        else:
            print(f"❌ No subscription data and no completed payments")
            print(f"❌ User needs to make a payment first")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_status()
