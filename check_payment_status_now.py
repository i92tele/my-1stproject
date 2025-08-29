#!/usr/bin/env python3
"""
Check the current status of the payment that was just cancelled.
"""

import sqlite3
import sys
import os
from datetime import datetime

def check_payment_status_now():
    """Check the current status of the recently cancelled payment."""
    
    db_path = "bot_database.db"
    payment_id = "TON_b9f2dcd602414711"
    
    try:
        print(f"🔍 CHECKING PAYMENT STATUS: {payment_id}")
        print("=" * 60)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check the payment details
        cursor.execute('''
            SELECT payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, 
                   created_at, updated_at, expires_at, tier, timeout_minutes, 
                   verification_attempts, last_verification_at, manual_verification
            FROM payments WHERE payment_id = ?
        ''', (payment_id,))
        
        payment_data = cursor.fetchone()
        
        if payment_data:
            payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, created_at, updated_at, expires_at, tier, timeout_minutes, verification_attempts, last_verification_at, manual_verification = payment_data
            
            print(f"Payment ID: {payment_id}")
            print(f"Status: {status}")
            print(f"Created: {created_at}")
            print(f"Updated: {updated_at}")
            print(f"Verification Attempts: {verification_attempts}")
            print(f"Last Verification: {last_verification_at}")
            print(f"Manual Verification: {manual_verification}")
            
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
                    print(f"  Expires in: {expires_dt - datetime.now()}")
        
        # Check recent payment updates
        print(f"\nRecent payment updates:")
        cursor.execute('''
            SELECT payment_id, status, created_at, updated_at
            FROM payments 
            WHERE user_id = ? 
            AND created_at >= '2025-08-28 17:50:00'
            ORDER BY created_at DESC
        ''', (user_id,))
        
        recent_payments = cursor.fetchall()
        for payment in recent_payments:
            pid, pstatus, pcreated, pupdated = payment
            print(f"  {pid}: {pstatus} - created: {pcreated}, updated: {pupdated}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_payment_status_now()
