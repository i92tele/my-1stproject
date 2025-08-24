#!/usr/bin/env python3
"""
Fix Slots - Reset timestamps to make all slots due for posting
"""

import sqlite3
from datetime import datetime, timedelta

def fix_slots():
    """Reset timestamps to make all slots due for posting."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Fixing slots to make them due for posting...")
        
        # Reset user slot timestamps to 2 hours ago
        old_timestamp = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE ad_slots 
            SET last_sent_at = ?
            WHERE is_active = 1 AND content IS NOT NULL AND content != ''
        """, (old_timestamp,))
        
        user_updated = cursor.rowcount
        print(f"✅ Reset {user_updated} user slot timestamps")
        
        # Reset admin slot timestamps to 2 hours ago
        cursor.execute("""
            UPDATE admin_ad_slots 
            SET last_sent_at = ?
            WHERE is_active = 1 AND content IS NOT NULL AND content != ''
        """, (old_timestamp,))
        
        admin_updated = cursor.rowcount
        print(f"✅ Reset {admin_updated} admin slot timestamps")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Total slots fixed: {user_updated + admin_updated}")
        print("🎯 All active slots should now be due for posting!")
        print("💡 Restart the scheduler to see the changes")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    fix_slots()
