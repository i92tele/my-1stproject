#!/usr/bin/env python3
"""
Extend subscription for Slot 79
"""

import sqlite3
from datetime import datetime, timedelta

def extend_subscription():
    """Extend subscription for Slot 79."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔄 Extending subscription for Slot 79...")
        
        # Get current subscription expiry
        cursor.execute("""
            SELECT u.user_id, u.username, u.subscription_expires
            FROM users u
            JOIN ad_slots s ON u.user_id = s.user_id
            WHERE s.id = 79
        """)
        result = cursor.fetchone()
        
        if result:
            user_id, username, expires = result
            print(f"  User {user_id} ({username}):")
            print(f"    Current expiry: {expires}")
            
            # Extend subscription by 30 days
            new_expiry = datetime.now() + timedelta(days=30)
            new_expiry_str = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                UPDATE users 
                SET subscription_expires = ?
                WHERE user_id = ?
            """, (new_expiry_str, user_id))
            
            conn.commit()
            print(f"    ✅ Extended to: {new_expiry_str}")
        else:
            print("❌ Slot 79 not found")
        
        conn.close()
        print("✅ Subscription extended!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    extend_subscription()
