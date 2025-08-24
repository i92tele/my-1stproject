#!/usr/bin/env python3
"""
Check Timestamps

This script checks the current timestamp status of ad slots to see if they were updated after posting
"""

import sqlite3
import sys
from datetime import datetime

def check_timestamps():
    """Check the current timestamp status of ad slots."""
    try:
        print("🔍 Checking ad slot timestamps...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Get current time for comparison
        now = datetime.now()
        print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check user ad slots
        print("📋 USER AD SLOTS:")
        print("-" * 80)
        cursor.execute("""
            SELECT id, content, last_sent_at, is_active, 
                   CASE 
                       WHEN last_sent_at IS NULL THEN 'NEVER SENT'
                       ELSE ROUND((julianday('now') - julianday(last_sent_at)) * 24 * 60, 1)
                   END as minutes_ago
            FROM ad_slots 
            WHERE is_active = 1 AND content IS NOT NULL AND content != ''
            ORDER BY last_sent_at ASC NULLS FIRST
        """)
        
        user_slots = cursor.fetchall()
        if user_slots:
            print("ID | Content (first 30 chars) | Last Sent | Minutes Ago | Status")
            print("-" * 80)
            for slot in user_slots:
                slot_id, content, last_sent, is_active, minutes_ago = slot
                content_preview = content[:30] + "..." if len(content) > 30 else content
                
                if last_sent is None:
                    status = "🟡 NEVER SENT"
                elif minutes_ago == "NEVER SENT":
                    status = "🟡 NEVER SENT"
                elif float(minutes_ago) < 5:
                    status = "🟢 RECENTLY UPDATED"
                elif float(minutes_ago) < 60:
                    status = "🟡 SENT RECENTLY"
                else:
                    status = "🔴 OLD TIMESTAMP"
                
                print(f"{slot_id:2} | {content_preview:30} | {last_sent or 'NULL':19} | {minutes_ago:>10} | {status}")
        else:
            print("No active user slots found")
        
        print()
        
        # Check admin ad slots
        print("📋 ADMIN AD SLOTS:")
        print("-" * 80)
        cursor.execute("""
            SELECT id, content, last_sent_at, is_active,
                   CASE 
                       WHEN last_sent_at IS NULL THEN 'NEVER SENT'
                       ELSE ROUND((julianday('now') - julianday(last_sent_at)) * 24 * 60, 1)
                   END as minutes_ago
            FROM admin_ad_slots 
            WHERE is_active = 1 AND content IS NOT NULL AND content != ''
            ORDER BY last_sent_at ASC NULLS FIRST
        """)
        
        admin_slots = cursor.fetchall()
        if admin_slots:
            print("ID | Content (first 30 chars) | Last Sent | Minutes Ago | Status")
            print("-" * 80)
            for slot in admin_slots:
                slot_id, content, last_sent, is_active, minutes_ago = slot
                content_preview = content[:30] + "..." if len(content) > 30 else content
                
                if last_sent is None:
                    status = "🟡 NEVER SENT"
                elif minutes_ago == "NEVER SENT":
                    status = "🟡 NEVER SENT"
                elif float(minutes_ago) < 5:
                    status = "🟢 RECENTLY UPDATED"
                elif float(minutes_ago) < 60:
                    status = "🟡 SENT RECENTLY"
                else:
                    status = "🔴 OLD TIMESTAMP"
                
                print(f"{slot_id:2} | {content_preview:30} | {last_sent or 'NULL':19} | {minutes_ago:>10} | {status}")
        else:
            print("No active admin slots found")
        
        print()
        
        # Summary
        print("📊 SUMMARY:")
        print("-" * 40)
        
        # Count recently updated slots (less than 5 minutes ago)
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NOT NULL 
            AND (julianday('now') - julianday(last_sent_at)) * 24 * 60 < 5
        """)
        recent_user = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NOT NULL 
            AND (julianday('now') - julianday(last_sent_at)) * 24 * 60 < 5
        """)
        recent_admin = cursor.fetchone()[0]
        
        print(f"🟢 Recently updated (last 5 min): {recent_user} user + {recent_admin} admin = {recent_user + recent_admin} total")
        
        # Count slots with old timestamps
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NOT NULL 
            AND (julianday('now') - julianday(last_sent_at)) * 24 * 60 > 60
        """)
        old_user = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NOT NULL 
            AND (julianday('now') - julianday(last_sent_at)) * 24 * 60 > 60
        """)
        old_admin = cursor.fetchone()[0]
        
        print(f"🔴 Old timestamps (>1 hour): {old_user} user + {old_admin} admin = {old_user + old_admin} total")
        
        # Count never sent slots
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        never_user = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 AND last_sent_at IS NULL
        """)
        never_admin = cursor.fetchone()[0]
        
        print(f"🟡 Never sent: {never_user} user + {never_admin} admin = {never_user + never_admin} total")
        
        conn.close()
        
        # Conclusion
        print()
        if recent_user + recent_admin > 0:
            print("✅ TIMESTAMPS ARE BEING UPDATED!")
            print("The bot is successfully updating timestamps after posting.")
        else:
            print("❌ TIMESTAMPS ARE NOT BEING UPDATED!")
            print("The bot is not updating timestamps after posting.")
            print("This will cause spam issues.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking timestamps: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("TIMESTAMP STATUS CHECK")
    print("=" * 80)
    
    success = check_timestamps()
    
    if success:
        print("\n✅ Timestamp check completed successfully!")
    else:
        print("\n❌ Timestamp check failed!")
    
    sys.exit(0 if success else 1)
