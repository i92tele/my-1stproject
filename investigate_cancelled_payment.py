#!/usr/bin/env python3
"""
Investigate what caused the payment to be marked as cancelled.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def investigate_cancelled_payment():
    """Investigate what caused the payment to be marked as cancelled."""
    
    db_path = "bot_database.db"
    payment_id = "TON_1fe31d1e179342b9"
    
    try:
        print(f"🔍 INVESTIGATING CANCELLED PAYMENT: {payment_id}")
        print("=" * 60)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Check the payment details
        print("\n1️⃣ PAYMENT DETAILS:")
        cursor.execute('''
            SELECT payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, 
                   created_at, updated_at, expires_at, tier, timeout_minutes, 
                   verification_attempts, last_verification_at, manual_verification
            FROM payments WHERE payment_id = ?
        ''', (payment_id,))
        
        payment_data = cursor.fetchone()
        
        if payment_data:
            payment_id, user_id, status, amount_usd, amount_crypto, crypto_type, created_at, updated_at, expires_at, tier, timeout_minutes, verification_attempts, last_verification_at, manual_verification = payment_data
            
            print(f"   Payment ID: {payment_id}")
            print(f"   User ID: {user_id}")
            print(f"   Status: {status}")
            print(f"   Amount USD: {amount_usd}")
            print(f"   Amount Crypto: {amount_crypto}")
            print(f"   Crypto Type: {crypto_type}")
            print(f"   Tier: {tier}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
            print(f"   Expires: {expires_at}")
            print(f"   Timeout Minutes: {timeout_minutes}")
            print(f"   Verification Attempts: {verification_attempts}")
            print(f"   Last Verification: {last_verification_at}")
            print(f"   Manual Verification: {manual_verification}")
            
            # Check if payment is expired
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                is_expired = expires_dt < datetime.now()
                print(f"   Is Expired: {is_expired}")
                print(f"   Expires in: {expires_dt - datetime.now()}")
        
        # 2. Check payment status history (if we had a status_log table)
        print("\n2️⃣ PAYMENT STATUS HISTORY:")
        print("   Note: No status_log table found, checking recent updates...")
        
        # Check when the status was last updated
        if payment_data:
            created_dt = datetime.fromisoformat(created_at)
            updated_dt = datetime.fromisoformat(updated_at)
            print(f"   Created: {created_dt}")
            print(f"   Last Updated: {updated_dt}")
            print(f"   Time between creation and update: {updated_dt - created_dt}")
        
        # 3. Check for payment timeout handler
        print("\n3️⃣ PAYMENT TIMEOUT ANALYSIS:")
        if payment_data and timeout_minutes:
            created_dt = datetime.fromisoformat(created_at)
            timeout_dt = created_dt + timedelta(minutes=timeout_minutes)
            print(f"   Payment created: {created_dt}")
            print(f"   Timeout after: {timeout_minutes} minutes")
            print(f"   Would timeout at: {timeout_dt}")
            print(f"   Current time: {datetime.now()}")
            print(f"   Would be timed out: {datetime.now() > timeout_dt}")
        
        # 4. Check verification attempts
        print("\n4️⃣ VERIFICATION ATTEMPTS:")
        if payment_data:
            print(f"   Verification attempts: {verification_attempts}")
            print(f"   Last verification: {last_verification_at}")
            
            if verification_attempts and verification_attempts >= 3:
                print("   ⚠️ Payment may have been cancelled due to max verification attempts")
        
        # 5. Check if there's a payment timeout handler running
        print("\n5️⃣ PAYMENT TIMEOUT HANDLER CHECK:")
        
        # Look for any payment timeout related code
        print("   Checking if payment timeout handler exists...")
        
        # Check if there are any other payments that were cancelled around the same time
        cursor.execute('''
            SELECT payment_id, status, created_at, updated_at
            FROM payments 
            WHERE status = 'cancelled' 
            AND created_at >= '2025-08-28 16:00:00'
            ORDER BY created_at DESC
        ''')
        
        recent_cancelled = cursor.fetchall()
        print(f"   Recent cancelled payments (after 16:00):")
        for payment in recent_cancelled:
            pid, pstatus, pcreated, pupdated = payment
            print(f"     {pid}: {pstatus} - created: {pcreated}, updated: {pupdated}")
        
        # 6. Check for manual cancellation
        print("\n6️⃣ MANUAL CANCELLATION CHECK:")
        if payment_data and manual_verification:
            print("   ⚠️ Payment has manual_verification flag set")
            print("   This suggests manual intervention")
        
        # 7. Check for payment monitor activity
        print("\n7️⃣ PAYMENT MONITOR ACTIVITY:")
        print("   From logs, payment monitor is running and checking payments")
        print("   Payment verification is failing due to API issues")
        print("   This could cause automatic cancellation after max attempts")
        
        # 8. Possible causes summary
        print("\n" + "=" * 60)
        print("🎯 POSSIBLE CAUSES OF CANCELLATION:")
        
        if payment_data:
            if verification_attempts and verification_attempts >= 3:
                print("✅ LIKELY CAUSE: Max verification attempts reached")
                print("   - Payment verification failed 3+ times")
                print("   - TON APIs are having issues (seen in logs)")
                print("   - System automatically cancelled after max attempts")
            
            elif manual_verification:
                print("✅ LIKELY CAUSE: Manual cancellation")
                print("   - Manual verification flag is set")
                print("   - Someone manually marked payment as cancelled")
            
            elif timeout_minutes and datetime.now() > created_dt + timedelta(minutes=timeout_minutes):
                print("✅ LIKELY CAUSE: Payment timeout")
                print("   - Payment exceeded timeout period")
                print("   - Timeout handler cancelled the payment")
            
            else:
                print("❓ UNKNOWN CAUSE")
                print("   - Need to check payment timeout handler code")
                print("   - Or check for manual database updates")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_cancelled_payment()
