#!/usr/bin/env python3
"""
Check Slots Status - See why slots are not being detected as due for posting
"""

import sqlite3
from datetime import datetime, timedelta

def check_slots_status():
    """Check the current status of all ad slots."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔍 Checking Ad Slots Status...")
        print("=" * 50)
        
        # Check user slots
        print("\n👥 USER SLOTS:")
        cursor.execute("""
            SELECT id, user_id, is_active, is_paused, content, interval_minutes, last_sent_at
            FROM ad_slots 
            ORDER BY id
        """)
        user_slots = cursor.fetchall()
        
        for slot in user_slots:
            slot_id, user_id, is_active, is_paused, content, interval, last_sent = slot
            status = []
            if is_active:
                status.append("✅ Active")
            else:
                status.append("❌ Inactive")
            
            if is_paused:
                status.append("⏸️ Paused")
            else:
                status.append("▶️ Not Paused")
            
            if content and content.strip():
                status.append("📝 Has Content")
            else:
                status.append("📝 No Content")
            
            print(f"  Slot {slot_id} (User {user_id}): {' | '.join(status)}")
            print(f"    Interval: {interval} min | Last sent: {last_sent}")
        
        # Check admin slots
        print("\n👑 ADMIN SLOTS:")
        cursor.execute("""
            SELECT id, is_active, is_paused, content, interval_minutes, last_sent_at
            FROM admin_ad_slots 
            ORDER BY id
        """)
        admin_slots = cursor.fetchall()
        
        for slot in admin_slots:
            slot_id, is_active, is_paused, content, interval, last_sent = slot
            status = []
            if is_active:
                status.append("✅ Active")
            else:
                status.append("❌ Inactive")
            
            if is_paused:
                status.append("⏸️ Paused")
            else:
                status.append("▶️ Not Paused")
            
            if content and content.strip():
                status.append("📝 Has Content")
            else:
                status.append("📝 No Content")
            
            print(f"  Admin Slot {slot_id}: {' | '.join(status)}")
            print(f"    Interval: {interval} min | Last sent: {last_sent}")
        
        # Check which slots should be due for posting
        print("\n⏰ SLOTS DUE FOR POSTING:")
        now = datetime.now()
        
        # Check user slots due for posting
        cursor.execute("""
            SELECT s.id, s.user_id, s.interval_minutes, s.last_sent_at, u.username, u.subscription_expires
            FROM ad_slots s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
        """)
        user_due_slots = cursor.fetchall()
        
        print(f"  User slots that should be due: {len(user_due_slots)}")
        for slot in user_due_slots:
            slot_id, user_id, interval, last_sent, username, expires = slot
            if last_sent:
                last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                next_due = last_sent_dt + timedelta(minutes=interval)
                time_until_due = next_due - now
                if time_until_due.total_seconds() <= 0:
                    status = "✅ DUE NOW"
                else:
                    status = f"⏳ Due in {time_until_due}"
            else:
                status = "✅ DUE NOW (never sent)"
            
            print(f"    Slot {slot_id} (User {user_id}): {status}")
        
        # Check admin slots due for posting
        cursor.execute("""
            SELECT id, interval_minutes, last_sent_at
            FROM admin_ad_slots
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
        """)
        admin_due_slots = cursor.fetchall()
        
        print(f"  Admin slots that should be due: {len(admin_due_slots)}")
        for slot in admin_due_slots:
            slot_id, interval, last_sent = slot
            if last_sent:
                last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                next_due = last_sent_dt + timedelta(minutes=interval)
                time_until_due = next_due - now
                if time_until_due.total_seconds() <= 0:
                    status = "✅ DUE NOW"
                else:
                    status = f"⏳ Due in {time_until_due}"
            else:
                status = "✅ DUE NOW (never sent)"
            
            print(f"    Admin Slot {slot_id}: {status}")
        
        # Check if there are any paused slots
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1 AND is_paused = 1")
        paused_user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1 AND is_paused = 1")
        paused_admin_count = cursor.fetchone()[0]
        
        print(f"\n📊 SUMMARY:")
        print(f"  Paused user slots: {paused_user_count}")
        print(f"  Paused admin slots: {paused_admin_count}")
        print(f"  Total slots that should be due: {len(user_due_slots) + len(admin_due_slots)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_slots_status()
