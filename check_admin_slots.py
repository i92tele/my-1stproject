#!/usr/bin/env python3
"""
Check Admin Slots

This script checks the status of admin ad slots to see why they're not being posted
"""

import sqlite3
import sys
from datetime import datetime

def check_admin_slots():
    """Check the status of admin ad slots."""
    try:
        print("🔍 Checking admin ad slots status...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Get current time for comparison
        now = datetime.now()
        print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check if admin_ad_slots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots';")
        if not cursor.fetchone():
            print("❌ admin_ad_slots table doesn't exist!")
            return False
        
        print("✅ admin_ad_slots table exists")
        
        # Get all admin slots
        cursor.execute("""
            SELECT id, slot_number, content, destinations, is_active, interval_minutes, last_sent_at,
                   CASE 
                       WHEN last_sent_at IS NULL THEN 'NEVER SENT'
                       ELSE ROUND((julianday('now') - julianday(last_sent_at)) * 24 * 60, 1)
                   END as minutes_ago
            FROM admin_ad_slots 
            ORDER BY slot_number
        """)
        
        admin_slots = cursor.fetchall()
        
        if not admin_slots:
            print("❌ No admin slots found in database!")
            return False
        
        print(f"📋 Found {len(admin_slots)} admin slots")
        print()
        
        # Display admin slots
        print("📋 ADMIN AD SLOTS DETAILS:")
        print("-" * 100)
        print("ID | Slot | Content (first 20 chars) | Destinations | Active | Interval | Last Sent | Minutes Ago | Status")
        print("-" * 100)
        
        active_slots = 0
        slots_with_content = 0
        slots_due_for_posting = 0
        
        for slot in admin_slots:
            slot_id, slot_number, content, destinations, is_active, interval_minutes, last_sent, minutes_ago = slot
            
            content_preview = content[:20] + "..." if content and len(content) > 20 else (content or "NULL")
            destinations_preview = destinations[:15] + "..." if destinations and len(destinations) > 15 else (destinations or "NULL")
            
            # Determine status
            if not is_active:
                status = "🔴 INACTIVE"
            elif not content or content.strip() == "":
                status = "🟡 NO CONTENT"
            elif not destinations or destinations.strip() == "":
                status = "🟡 NO DESTINATIONS"
            elif last_sent is None:
                status = "🟢 DUE (NEVER SENT)"
                slots_due_for_posting += 1
            elif minutes_ago == "NEVER SENT":
                status = "🟢 DUE (NEVER SENT)"
                slots_due_for_posting += 1
            elif float(minutes_ago) >= interval_minutes:
                status = "🟢 DUE FOR POSTING"
                slots_due_for_posting += 1
            else:
                status = "🟡 NOT DUE"
            
            if is_active:
                active_slots += 1
            if content and content.strip() != "":
                slots_with_content += 1
            
            print(f"{slot_id:2} | {slot_number:4} | {content_preview:20} | {destinations_preview:15} | {is_active:6} | {interval_minutes:8} | {last_sent or 'NULL':19} | {minutes_ago:>10} | {status}")
        
        print()
        
        # Summary
        print("📊 ADMIN SLOTS SUMMARY:")
        print("-" * 40)
        print(f"📝 Total admin slots: {len(admin_slots)}")
        print(f"✅ Active slots: {active_slots}")
        print(f"📄 Slots with content: {slots_with_content}")
        print(f"🟢 Slots due for posting: {slots_due_for_posting}")
        print(f"🔴 Inactive slots: {len(admin_slots) - active_slots}")
        print(f"🟡 Slots without content: {len(admin_slots) - slots_with_content}")
        
        # Check if admin slots would be included in get_active_ads_to_send
        print()
        print("🔍 CHECKING IF ADMIN SLOTS WOULD BE INCLUDED IN POSTING:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
            AND (
                last_sent_at IS NULL 
                OR datetime('now') >= datetime(last_sent_at, '+' || COALESCE(interval_minutes, 60) || ' minutes')
            )
        """)
        
        eligible_admin_slots = cursor.fetchone()[0]
        print(f"✅ Admin slots eligible for posting: {eligible_admin_slots}")
        
        if eligible_admin_slots > 0:
            print("✅ Admin slots SHOULD be included in posting cycle")
        else:
            print("❌ Admin slots will NOT be included in posting cycle")
            print("   Reasons:")
            if active_slots == 0:
                print("   - No active admin slots")
            if slots_with_content == 0:
                print("   - No admin slots with content")
            if slots_due_for_posting == 0:
                print("   - No admin slots due for posting")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking admin slots: {e}")
        return False

if __name__ == "__main__":
    print("=" * 100)
    print("ADMIN SLOTS STATUS CHECK")
    print("=" * 100)
    
    success = check_admin_slots()
    
    if success:
        print("\n✅ Admin slots check completed successfully!")
    else:
        print("\n❌ Admin slots check failed!")
    
    sys.exit(0 if success else 1)
