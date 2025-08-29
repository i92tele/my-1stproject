#!/usr/bin/env python3
"""
Manually fix the user's subscription in the database.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def fix_subscription_manual():
    """Manually fix the user's subscription."""
    
    db_path = "bot_database.db"
    user_id = 7593457389
    
    try:
        print("🔧 Manually fixing user subscription...")
        
        # Connect to database
        conn = sqlite3.connect(db_path, timeout=60.0)
        cursor = conn.cursor()
        
        # Check current state
        print("\n📊 Current state:")
        cursor.execute("""
            SELECT user_id, subscription_tier, subscription_expires, created_at, updated_at
            FROM users WHERE user_id = ?
        """, (user_id,))
        current = cursor.fetchone()
        print(f"Current: {current}")
        
        # Check payments
        cursor.execute("""
            SELECT payment_id, status, amount_usd, crypto_type, created_at
            FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        payment = cursor.fetchone()
        print(f"Latest payment: {payment}")
        
        if not current:
            print("❌ User not found, creating user...")
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, subscription_tier, subscription_expires, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                f"user_{user_id}",
                "User",
                None,
                "basic",
                (datetime.now() + timedelta(days=30)).isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        else:
            print("✅ User exists, updating subscription...")
            cursor.execute("""
                UPDATE users 
                SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
                WHERE user_id = ?
            """, (
                "basic",
                (datetime.now() + timedelta(days=30)).isoformat(),
                datetime.now().isoformat(),
                user_id
            ))
        
        # Update payment status to completed
        if payment:
            print("✅ Updating payment status to completed...")
            cursor.execute("""
                UPDATE payments 
                SET status = ?, updated_at = ?
                WHERE payment_id = ?
            """, ("completed", datetime.now().isoformat(), payment[0]))
        
        # Commit changes
        conn.commit()
        print("✅ Changes committed")
        
        # Verify the fix
        print("\n🔍 Verifying fix:")
        cursor.execute("""
            SELECT user_id, subscription_tier, subscription_expires, created_at, updated_at
            FROM users WHERE user_id = ?
        """, (user_id,))
        fixed = cursor.fetchone()
        print(f"Fixed: {fixed}")
        
        if payment:
            cursor.execute("SELECT status FROM payments WHERE payment_id = ?", (payment[0],))
            payment_status = cursor.fetchone()
            print(f"Payment status: {payment_status}")
        
        conn.close()
        
        print("\n🎉 MANUAL FIX COMPLETED!")
        print("User should now have an active subscription")
        
    except Exception as e:
        print(f"❌ Error fixing subscription: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_subscription_manual()
