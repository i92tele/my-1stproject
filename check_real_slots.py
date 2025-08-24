#!/usr/bin/env python3
"""
Check Real Slots
This script checks what slots actually exist in the database
"""

import sqlite3
import sys
import os
from datetime import datetime

def check_real_slots():
    """Check what slots actually exist in the database."""
    try:
        print("🔍 Checking Real Slots in Database...")
        print("=" * 60)
        
        # Check if database exists
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check user slots
        print("\n👥 USER SLOTS:")
        print("-" * 40)
        cursor.execute("""
            SELECT id, user_id, slot_number, is_active, content, last_sent_at, interval_minutes
            FROM ad_slots 
            ORDER BY id
        """)
        
        user_slots = cursor.fetchall()
        if user_slots:
            print(f"Found {len(user_slots)} user slots:")
            for slot in user_slots:
                slot_id, user_id, slot_num, is_active, content, last_sent, interval = slot
                status = "✅ Active" if is_active else "❌ Inactive"
                has_content = "📝 Has Content" if content and content.strip() else "📝 No Content"
                print(f"  Slot {slot_id} (User {user_id}, Slot {slot_num}): {status} | {has_content}")
                if last_sent:
                    print(f"    Last sent: {last_sent}, Interval: {interval} min")
        else:
            print("No user slots found")
        
        # Check admin slots
        print("\n👑 ADMIN SLOTS:")
        print("-" * 40)
        cursor.execute("""
            SELECT id, slot_number, is_active, content, last_sent_at, interval_minutes
            FROM admin_ad_slots 
            ORDER BY slot_number
        """)
        
        admin_slots = cursor.fetchall()
        if admin_slots:
            print(f"Found {len(admin_slots)} admin slots:")
            for slot in admin_slots:
                slot_id, slot_num, is_active, content, last_sent, interval = slot
                status = "✅ Active" if is_active else "❌ Inactive"
                has_content = "📝 Has Content" if content and content.strip() else "📝 No Content"
                print(f"  Admin Slot {slot_id} (Slot {slot_num}): {status} | {has_content}")
                if last_sent:
                    print(f"    Last sent: {last_sent}, Interval: {interval} min")
        else:
            print("No admin slots found")
        
        # Check what get_active_ads_to_send would return
        print("\n🔍 ACTIVE ADS TO SEND:")
        print("-" * 40)
        
        # User slots due
        cursor.execute("""
            SELECT COUNT(*) FROM ad_slots s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
            AND (
                s.last_sent_at IS NULL 
                OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
            )
        """)
        
        user_due = cursor.fetchone()[0]
        print(f"User slots due for posting: {user_due}")
        
        # Admin slots due
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
            AND (
                last_sent_at IS NULL 
                OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
            )
        """)
        
        admin_due = cursor.fetchone()[0]
        print(f"Admin slots due for posting: {admin_due}")
        
        total_due = user_due + admin_due
        print(f"Total slots due for posting: {total_due}")
        
        if total_due > 0:
            print("\n📋 DETAILS OF DUE SLOTS:")
            print("-" * 40)
            
            # Show user slots due
            if user_due > 0:
                cursor.execute("""
                    SELECT s.id, s.user_id, s.slot_number, s.content, s.last_sent_at, s.interval_minutes
                    FROM ad_slots s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE s.is_active = 1 
                    AND s.content IS NOT NULL 
                    AND s.content != ''
                    AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
                    AND (
                        s.last_sent_at IS NULL 
                        OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
                    )
                """)
                
                user_due_slots = cursor.fetchall()
                for slot in user_due_slots:
                    slot_id, user_id, slot_num, content, last_sent, interval = slot
                    print(f"  User Slot {slot_id} (User {user_id}, Slot {slot_num}): {content[:50]}...")
            
            # Show admin slots due
            if admin_due > 0:
                cursor.execute("""
                    SELECT id, slot_number, content, last_sent_at, interval_minutes
                    FROM admin_ad_slots 
                    WHERE is_active = 1 
                    AND content IS NOT NULL 
                    AND content != ''
                    AND (
                        last_sent_at IS NULL 
                        OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
                    )
                """)
                
                admin_due_slots = cursor.fetchall()
                for slot in admin_due_slots:
                    slot_id, slot_num, content, last_sent, interval = slot
                    print(f"  Admin Slot {slot_id} (Slot {slot_num}): {content[:50]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking real slots: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("REAL SLOTS DIAGNOSTIC TOOL")
    print("=" * 60)
    check_real_slots()
    print("\n" + "=" * 60)
