#!/usr/bin/env python3
"""
Direct database state check to see what's happening with the user's subscription.
"""

import sqlite3
import sys
import os
from datetime import datetime

def check_database_state():
    """Check the current database state directly."""
    
    db_path = "bot_database.db"
    user_id = 7593457389
    
    try:
        print("🔍 Checking database state directly...")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check user table
        print("\n📊 USER TABLE:")
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ User found: {user}")
            
            # Get column names
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Columns: {columns}")
            
            # Check subscription fields specifically
            cursor.execute("""
                SELECT user_id, subscription_tier, subscription_expires, created_at, updated_at
                FROM users WHERE user_id = ?
            """, (user_id,))
            subscription_data = cursor.fetchone()
            print(f"Subscription data: {subscription_data}")
        else:
            print("❌ User not found")
        
        # Check payments table
        print("\n💰 PAYMENTS TABLE:")
        cursor.execute("""
            SELECT payment_id, user_id, status, amount_usd, crypto_type, created_at, updated_at, expires_at
            FROM payments WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        payments = cursor.fetchall()
        
        print(f"Found {len(payments)} payments:")
        for payment in payments:
            print(f"  Payment: {payment}")
        
        # Check for any database locks
        print("\n🔒 DATABASE LOCKS:")
        cursor.execute("PRAGMA busy_timeout")
        busy_timeout = cursor.fetchone()
        print(f"Busy timeout: {busy_timeout}")
        
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()
        print(f"Journal mode: {journal_mode}")
        
        # Check if database is locked
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()
            print(f"Database accessible: ✅ (user count: {count[0]})")
        except Exception as e:
            print(f"Database locked: ❌ {e}")
        
        conn.close()
        
        print("\n🎯 SUMMARY:")
        if user:
            if subscription_data[1]:  # subscription_tier
                print("✅ User has subscription tier")
            else:
                print("❌ User has no subscription tier")
                
            if subscription_data[2]:  # subscription_expires
                print("✅ User has subscription expiry")
                # Check if subscription is active by comparing expiry with current time
                expiry = datetime.fromisoformat(subscription_data[2])
                if expiry > datetime.now():
                    print("✅ User subscription is active")
                else:
                    print("❌ User subscription has expired")
            else:
                print("❌ User has no subscription expiry")
        else:
            print("❌ User not found in database")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_state()
