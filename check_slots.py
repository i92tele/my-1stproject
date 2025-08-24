#!/usr/bin/env python3
"""
Check current status of ad slots
"""

import sqlite3

def check_slots():
    """Check current status of ad slots."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔍 Checking Ad Slots Status...")
        
        # Check user slots
        cursor.execute("""
            SELECT id, user_id, is_active, is_paused, content 
            FROM ad_slots 
            WHERE is_active = 1
            ORDER BY id
        """)
        active_slots = cursor.fetchall()
        
        print(f"\n👥 Active User Slots: {len(active_slots)}")
        for slot in active_slots:
            slot_id, user_id, is_active, is_paused, content = slot
            status = "⏸️ Paused" if is_paused else "▶️ Active"
            has_content = "📝 Has Content" if content and content.strip() else "📝 No Content"
            print(f"  Slot {slot_id} (User {user_id}): {status} | {has_content}")
        
        # Check admin slots
        cursor.execute("""
            SELECT id, is_active, content 
            FROM admin_ad_slots 
            WHERE is_active = 1
            ORDER BY id
        """)
        active_admin_slots = cursor.fetchall()
        
        print(f"\n👑 Active Admin Slots: {len(active_admin_slots)}")
        for slot in active_admin_slots:
            slot_id, is_active, content = slot
            has_content = "📝 Has Content" if content and content.strip() else "📝 No Content"
            print(f"  Admin Slot {slot_id}: {has_content}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_slots()
