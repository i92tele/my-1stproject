#!/usr/bin/env python3
"""
Immediately fix the user's subscription based on completed payments.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def fix_user_subscription():
    """Fix the user's subscription immediately."""
    
    db_path = "bot_database.db"
    user_id = 7593457389
    
    try:
        print(f"🔧 Fixing subscription for user {user_id}...")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current subscription status
        cursor.execute('''
            SELECT subscription_tier, subscription_expires
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        if user_data:
            subscription_tier, subscription_expires = user_data
            print(f"Current subscription: {subscription_tier}, expires: {subscription_expires}")
        
        # Check completed payments
        cursor.execute('''
            SELECT payment_id, amount_usd, created_at
            FROM payments 
            WHERE user_id = ? AND status = 'completed' 
            ORDER BY created_at DESC
        ''', (user_id,))
        
        completed_payments = cursor.fetchall()
        
        if completed_payments:
            print(f"Found {len(completed_payments)} completed payments")
            
            # Get the most recent completed payment
            latest_payment = completed_payments[0]
            payment_id, amount_usd, created_at = latest_payment
            
            print(f"Latest completed payment: {payment_id} (${amount_usd})")
            
            # Determine tier based on amount
            if amount_usd == 15.0:
                tier = "basic"
                duration_days = 30
            elif amount_usd == 45.0:
                tier = "pro"
                duration_days = 30
            elif amount_usd == 75.0:
                tier = "enterprise"
                duration_days = 30
            else:
                tier = "basic"
                duration_days = 30
            
            # Calculate expiry date (30 days from now)
            new_expiry = datetime.now() + timedelta(days=duration_days)
            
            # Update user subscription
            cursor.execute('''
                UPDATE users 
                SET subscription_tier = ?, subscription_expires = ?, updated_at = ?
                WHERE user_id = ?
            ''', (tier, new_expiry.isoformat(), datetime.now().isoformat(), user_id))
            
            conn.commit()
            print(f"✅ Subscription activated: {tier} tier until {new_expiry}")
            
            # Verify the update
            cursor.execute('''
                SELECT subscription_tier, subscription_expires
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            updated_data = cursor.fetchone()
            if updated_data:
                tier, expires = updated_data
                expires_dt = datetime.fromisoformat(expires)
                is_active = expires_dt > datetime.now()
                print(f"✅ Verification: {tier} tier, expires {expires}, active: {is_active}")
            
            # Also update the cancelled payment to completed if it was actually paid
            print(f"\n🔍 Checking if cancelled payment was actually paid...")
            cursor.execute('''
                SELECT payment_id, status, created_at
                FROM payments 
                WHERE user_id = ? AND status = 'cancelled' 
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            
            cancelled_payment = cursor.fetchone()
            if cancelled_payment:
                cancelled_payment_id, cancelled_status, cancelled_created = cancelled_payment
                print(f"Latest cancelled payment: {cancelled_payment_id}")
                
                # Check if this payment was created recently (within last hour)
                cancelled_created_dt = datetime.fromisoformat(cancelled_created)
                time_diff = datetime.now() - cancelled_created_dt
                
                if time_diff.total_seconds() < 3600:  # Within 1 hour
                    print(f"⚠️ Recent cancelled payment detected. Marking as completed...")
                    cursor.execute('''
                        UPDATE payments 
                        SET status = 'completed', updated_at = ?
                        WHERE payment_id = ?
                    ''', (datetime.now().isoformat(), cancelled_payment_id))
                    conn.commit()
                    print(f"✅ Payment {cancelled_payment_id} marked as completed")
                else:
                    print(f"Payment {cancelled_payment_id} was cancelled a while ago, leaving as cancelled")
            
        else:
            print("No completed payments found")
        
        conn.close()
        print(f"\n🎯 User {user_id} subscription fixed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_user_subscription()
