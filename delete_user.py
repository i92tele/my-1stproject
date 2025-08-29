#!/usr/bin/env python3
"""
Delete User Script

This script allows you to delete a specific user and all their associated data
by providing their user ID.

Usage: python3 delete_user.py <user_id>
"""

import sqlite3
import sys
import os
from datetime import datetime

def delete_user_by_id(user_id):
    """Delete a user and all their associated data."""
    try:
        print(f"🗑️  Deleting user {user_id} and all associated data...")
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # First, check if user exists
        cursor.execute("SELECT user_id, username, subscription_tier, created_at FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User {user_id} not found in database")
            return False
        
        print(f"👤 Found user: {user[1]} (@{user[1] or 'No username'})")
        print(f"   Subscription: {user[2] or 'None'}")
        print(f"   Created: {user[3]}")
        
        # Show what will be deleted
        print(f"\n📋 Data to be deleted:")
        
        # Count ad slots
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE user_id = ?", (user_id,))
        ad_slots_count = cursor.fetchone()[0]
        print(f"   📢 Ad slots: {ad_slots_count}")
        
        # Count payments
        cursor.execute("SELECT COUNT(*) FROM payments WHERE user_id = ?", (user_id,))
        payments_count = cursor.fetchone()[0]
        print(f"   💰 Payments: {payments_count}")
        
        # Count slot destinations
        cursor.execute("""
            SELECT COUNT(*) FROM slot_destinations sd
            JOIN ad_slots a ON sd.slot_id = a.id
            WHERE a.user_id = ?
        """, (user_id,))
        destinations_count = cursor.fetchone()[0]
        print(f"   🎯 Slot destinations: {destinations_count}")
        
        # Ask for confirmation
        confirm = input(f"\n⚠️  Are you sure you want to delete user {user_id} and all their data? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ Deletion cancelled")
            return False
        
        print(f"\n🧹 Starting deletion...")
        
        # Delete in order to maintain referential integrity
        
        # 1. Delete slot destinations first
        cursor.execute("""
            DELETE FROM slot_destinations 
            WHERE slot_id IN (SELECT id FROM ad_slots WHERE user_id = ?)
        """, (user_id,))
        deleted_destinations = cursor.rowcount
        print(f"   ✅ Deleted {deleted_destinations} slot destinations")
        
        # 2. Delete ad slots
        cursor.execute("DELETE FROM ad_slots WHERE user_id = ?", (user_id,))
        deleted_slots = cursor.rowcount
        print(f"   ✅ Deleted {deleted_slots} ad slots")
        
        # 3. Delete payments
        cursor.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
        deleted_payments = cursor.rowcount
        print(f"   ✅ Deleted {deleted_payments} payments")
        
        # 4. Delete message stats (if table exists)
        try:
            cursor.execute("DELETE FROM message_stats WHERE user_id = ?", (user_id,))
            deleted_stats = cursor.rowcount
            print(f"   ✅ Deleted {deleted_stats} message stats")
        except sqlite3.OperationalError:
            print(f"   ℹ️  No message_stats table found")
        
        # 5. Finally delete the user
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        deleted_user = cursor.rowcount
        print(f"   ✅ Deleted {deleted_user} user record")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print(f"\n🎉 Successfully deleted user {user_id} and all associated data!")
        print(f"📊 Summary:")
        print(f"   - User records: {deleted_user}")
        print(f"   - Ad slots: {deleted_slots}")
        print(f"   - Slot destinations: {deleted_destinations}")
        print(f"   - Payments: {deleted_payments}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting user {user_id}: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python3 delete_user.py <user_id>")
        print("Example: python3 delete_user.py 123456789")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("❌ Error: user_id must be a number")
        sys.exit(1)
    
    # Check if database exists
    if not os.path.exists("bot_database.db"):
        print("❌ Error: bot_database.db not found")
        sys.exit(1)
    
    # Delete the user
    success = delete_user_by_id(user_id)
    
    if success:
        print(f"\n✅ User {user_id} successfully deleted!")
    else:
        print(f"\n❌ Failed to delete user {user_id}")
        sys.exit(1)

if __name__ == "__main__":
    main()
