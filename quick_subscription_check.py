#!/usr/bin/env python3
"""
Quick subscription check and activation.
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def check_and_fix_subscription():
    """Check subscription status and fix if needed."""
    
    db_path = "bot_database.db"
    user_id = 7593457389
    
    try:
        print("🔍 Checking subscription status...")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check user subscription
        cursor.execute('''
            SELECT subscription_tier, subscription_expires, created_at, updated_at
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        
        if user_data:
            subscription_tier, subscription_expires, created_at, updated_at = user_data
            print(f"User {user_id} data:")
            print(f"  Subscription tier: {subscription_tier}")
            print(f"  Subscription expires: {subscription_expires}")
            print(f"  Created: {created_at}")
            print(f"  Updated: {updated_at}")
            
            # Check if subscription is active
            if subscription_expires:
                expires_dt = datetime.fromisoformat(subscription_expires)
                is_active = expires_dt > datetime.now()
                print(f"  Is active: {is_active}")
                print(f"  Expires in: {expires_dt - datetime.now()}")
            else:
                print("  No subscription expiry date")
                is_active = False
        else:
            print(f"User {user_id} not found in database")
            is_active = False
        
        # Check payments
        print(f"\n💰 Checking payments for user {user_id}...")
        cursor.execute('''
            SELECT payment_id, status, amount_usd, tier, created_at, updated_at
            FROM payments WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,))
        
        payments = cursor.fetchall()
        
        if payments:
            print(f"Found {len(payments)} payments:")
            for payment in payments:
                payment_id, status, amount_usd, tier, created_at, updated_at = payment
                print(f"  {payment_id}: {status} (${amount_usd}, {tier}) - {created_at}")
        else:
            print("No payments found")
        
        # If user has no active subscription but has completed payments, activate one
        if not is_active and payments:
            completed_payments = [p for p in payments if p[1] == 'completed']
            if completed_payments:
                print(f"\n⚠️ User has {len(completed_payments)} completed payments but no active subscription")
                print("Activating subscription...")
                
                # Get the most recent completed payment
                latest_payment = completed_payments[0]
                payment_id, status, amount_usd, tier, created_at, updated_at = latest_payment
                
                # Determine tier and duration
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
                
                # Calculate expiry date
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
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_fix_subscription()
