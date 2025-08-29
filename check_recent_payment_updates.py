#!/usr/bin/env python3
"""
Check recent payment updates to understand what caused the cancellation.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def check_recent_payment_updates():
    """Check recent payment updates to understand the cancellation."""
    
    db_path = "bot_database.db"
    payment_id = "TON_1fe31d1e179342b9"
    
    try:
        print(f"🔍 CHECKING RECENT PAYMENT UPDATES")
        print("=" * 60)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Check the specific payment details
        print(f"\n1️⃣ PAYMENT DETAILS:")
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
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
            print(f"   Verification Attempts: {verification_attempts}")
            print(f"   Last Verification: {last_verification_at}")
            print(f"   Manual Verification: {manual_verification}")
        
        # 2. Check all payments for this user around the same time
        print(f"\n2️⃣ ALL PAYMENTS FOR USER {user_id} (recent):")
        cursor.execute('''
            SELECT payment_id, status, created_at, updated_at
            FROM payments 
            WHERE user_id = ? 
            AND created_at >= '2025-08-28 16:30:00'
            ORDER BY created_at DESC
        ''', (user_id,))
        
        recent_payments = cursor.fetchall()
        for payment in recent_payments:
            pid, pstatus, pcreated, pupdated = payment
            print(f"   {pid}: {pstatus} - created: {pcreated}, updated: {pupdated}")
        
        # 3. Check if there are any other cancelled payments around the same time
        print(f"\n3️⃣ ALL CANCELLED PAYMENTS (recent):")
        cursor.execute('''
            SELECT payment_id, user_id, status, created_at, updated_at
            FROM payments 
            WHERE status = 'cancelled' 
            AND created_at >= '2025-08-28 16:30:00'
            ORDER BY created_at DESC
        ''', ())
        
        recent_cancelled = cursor.fetchall()
        for payment in recent_cancelled:
            pid, puser_id, pstatus, pcreated, pupdated = payment
            print(f"   {pid} (user: {puser_id}): {pstatus} - created: {pcreated}, updated: {pupdated}")
        
        # 4. Check if there's a pattern in the timing
        print(f"\n4️⃣ TIMING ANALYSIS:")
        if payment_data:
            created_dt = datetime.fromisoformat(created_at)
            updated_dt = datetime.fromisoformat(updated_at)
            time_diff = updated_dt - created_dt
            
            print(f"   Payment created: {created_dt}")
            print(f"   Payment cancelled: {updated_dt}")
            print(f"   Time difference: {time_diff}")
            print(f"   Time difference (seconds): {time_diff.total_seconds()}")
            
            # Check if this matches any known patterns
            if time_diff.total_seconds() < 300:  # Less than 5 minutes
                print(f"   ⚠️ Very quick cancellation - likely manual or automated")
            elif time_diff.total_seconds() < 1800:  # Less than 30 minutes
                print(f"   ⚠️ Quick cancellation - could be timeout or manual")
            else:
                print(f"   ✅ Normal timing - likely timeout")
        
        # 5. Check if there are any database triggers or constraints
        print(f"\n5️⃣ DATABASE SCHEMA CHECK:")
        cursor.execute("PRAGMA table_info(payments)")
        columns = cursor.fetchall()
        print(f"   Payments table columns:")
        for col in columns:
            print(f"     {col[1]}: {col[2]} (PK: {col[5]}, NotNull: {col[3]}, Default: {col[4]})")
        
        # 6. Check for any foreign key constraints or triggers
        print(f"\n6️⃣ DATABASE CONSTRAINTS:")
        cursor.execute("PRAGMA foreign_key_list(payments)")
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            print(f"   Foreign key constraints:")
            for fk in foreign_keys:
                print(f"     {fk}")
        else:
            print(f"   No foreign key constraints")
        
        # 7. Possible causes summary
        print(f"\n" + "=" * 60)
        print("🎯 POSSIBLE CAUSES OF CANCELLATION:")
        
        if payment_data:
            if verification_attempts == 0:
                print("✅ LIKELY CAUSE: Manual cancellation")
                print("   - No verification attempts made")
                print("   - Very quick cancellation (2 minutes)")
                print("   - Likely triggered by user action or admin")
            
            elif verification_attempts > 0:
                print("✅ LIKELY CAUSE: Failed verification")
                print("   - Verification attempts were made")
                print("   - Manual verification always returns False")
                print("   - System may have cancelled after max attempts")
            
            else:
                print("❓ UNKNOWN CAUSE")
                print("   - Need to check for other processes")
                print("   - Could be database trigger or external process")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_recent_payment_updates()
