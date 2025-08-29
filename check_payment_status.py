#!/usr/bin/env python3
"""
Check the specific payment status that's causing the "Payment Cancelled" issue.
"""

import sqlite3
import sys
import os
from datetime import datetime

def check_payment_status():
    """Check the payment status that's causing the issue."""
    
    db_path = "bot_database.db"
    payment_id = "TON_1fe31d1e179342b9"  # From the screenshot
    
    try:
        print(f"🔍 Checking payment status for: {payment_id}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check the specific payment
        cursor.execute('''
            SELECT payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, 
                   created_at, updated_at, expires_at, tier
            FROM payments WHERE payment_id = ?
        ''', (payment_id,))
        
        payment_data = cursor.fetchone()
        
        if payment_data:
            payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, created_at, updated_at, expires_at, tier = payment_data
            print(f"Payment found:")
            print(f"  Payment ID: {payment_id}")
            print(f"  User ID: {user_id}")
            print(f"  Status: {status}")
            print(f"  Amount USD: {amount_usd}")
            print(f"  Amount Crypto: {amount_crypto}")
            print(f"  Crypto Type: {crypto_type}")
            print(f"  Tier: {tier}")
            print(f"  Created: {created_at}")
            print(f"  Updated: {updated_at}")
            print(f"  Expires: {expires_at}")
            
            # Check if payment is expired
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                is_expired = expires_dt < datetime.now()
                print(f"  Is Expired: {is_expired}")
                print(f"  Expires in: {expires_dt - datetime.now()}")
            
            # Check user subscription
            cursor.execute('''
                SELECT subscription_tier, subscription_expires
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if user_data:
                subscription_tier, subscription_expires = user_data
                print(f"\nUser subscription:")
                print(f"  Tier: {subscription_tier}")
                print(f"  Expires: {subscription_expires}")
                
                if subscription_expires:
                    expires_dt = datetime.fromisoformat(subscription_expires)
                    is_active = expires_dt > datetime.now()
                    print(f"  Is Active: {is_active}")
            
            # Check all payments for this user
            print(f"\nAll payments for user {user_id}:")
            cursor.execute('''
                SELECT payment_id, status, amount_usd, created_at
                FROM payments WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,))
            
            all_payments = cursor.fetchall()
            for payment in all_payments:
                pid, pstatus, pamount, pcreated = payment
                print(f"  {pid}: {pstatus} (${pamount}) - {pcreated}")
            
        else:
            print(f"Payment {payment_id} not found in database")
            
            # Check if there are similar payment IDs
            cursor.execute('''
                SELECT payment_id, status, user_id, created_at
                FROM payments WHERE payment_id LIKE 'TON_%' ORDER BY created_at DESC LIMIT 10
            ''')
            
            similar_payments = cursor.fetchall()
            print(f"\nRecent TON payments:")
            for payment in similar_payments:
                pid, pstatus, puser_id, pcreated = payment
                print(f"  {pid}: {pstatus} (user: {puser_id}) - {pcreated}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_payment_status()
