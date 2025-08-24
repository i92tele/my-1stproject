#!/usr/bin/env python3
"""
Check Admin Slot 2 Status
This script checks why admin slot 2 is not being picked up by the scheduler
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta

def check_admin_slot_2():
    """Check the status of admin slot 2."""
    try:
        print("🔍 Checking Admin Slot 2 Status...")
        print("=" * 60)
        
        # Check if database exists
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if admin_ad_slots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots';")
        if not cursor.fetchone():
            print("❌ admin_ad_slots table doesn't exist!")
            return False
        
        print("✅ admin_ad_slots table exists")
        
        # Get admin slot 2 specifically
        cursor.execute("""
            SELECT id, slot_number, content, destinations, is_active, interval_minutes, last_sent_at,
                   CASE 
                       WHEN last_sent_at IS NULL THEN 'NEVER SENT'
                       ELSE ROUND((julianday('now') - julianday(last_sent_at)) * 24 * 60, 1)
                   END as minutes_ago
            FROM admin_ad_slots 
            WHERE slot_number = 2
        """)
        
        slot_2 = cursor.fetchone()
        
        if not slot_2:
            print("❌ Admin slot 2 not found!")
            return False
        
        slot_id, slot_number, content, destinations, is_active, interval, last_sent, minutes_ago = slot_2
        
        print(f"📋 Admin Slot 2 Details:")
        print(f"  ID: {slot_id}")
        print(f"  Slot Number: {slot_number}")
        print(f"  Active: {'✅ Yes' if is_active else '❌ No'}")
        print(f"  Has Content: {'✅ Yes' if content and content.strip() else '❌ No'}")
        print(f"  Content Preview: {content[:50] if content else 'None'}...")
        print(f"  Interval: {interval} minutes")
        print(f"  Last Sent: {last_sent}")
        print(f"  Minutes Ago: {minutes_ago}")
        
        # Check if it would be due for posting
        now = datetime.now()
        if last_sent:
            last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
            due_time = last_sent_dt + timedelta(minutes=interval)
            is_due = now >= due_time
            print(f"  Due Time: {due_time}")
            print(f"  Is Due: {'✅ Yes' if is_due else '❌ No'}")
        else:
            print(f"  Is Due: ✅ Yes (never sent)")
            is_due = True
        
        # Check destinations
        if destinations:
            try:
                import json
                dest_list = json.loads(destinations)
                print(f"  Destinations: {len(dest_list)} configured")
                for i, dest in enumerate(dest_list[:3]):
                    print(f"    {i+1}. {dest.get('destination_name', 'Unknown')} ({dest.get('destination_id', 'Unknown')})")
                if len(dest_list) > 3:
                    print(f"    ... and {len(dest_list) - 3} more")
            except:
                print(f"  Destinations: Error parsing JSON")
        else:
            print(f"  Destinations: None configured")
        
        # Check if it would be included in get_active_ads_to_send
        print("\n🔍 Checking if slot would be included in posting cycle:")
        print("-" * 50)
        
        if not is_active:
            print("❌ Slot is not active")
        elif not content or not content.strip():
            print("❌ Slot has no content")
        elif not is_due:
            print("❌ Slot is not due for posting")
        else:
            print("✅ Slot SHOULD be included in posting cycle")
        
        # Check what get_active_ads_to_send would return
        print("\n🔍 Simulating get_active_ads_to_send query:")
        print("-" * 50)
        
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
        
        eligible_count = cursor.fetchone()[0]
        print(f"✅ Admin slots eligible for posting: {eligible_count}")
        
        if eligible_count > 0:
            cursor.execute("""
                SELECT id, slot_number, content, last_sent_at, interval_minutes
                FROM admin_ad_slots 
                WHERE is_active = 1 
                AND content IS NOT NULL 
                AND content != ''
                AND (
                    last_sent_at IS NULL 
                    OR datetime('now') >= datetime(last_sent_at, '+' || COALESCE(interval_minutes, 60) || ' minutes')
                )
            """)
            
            eligible_slots = cursor.fetchall()
            print("Eligible admin slots:")
            for slot in eligible_slots:
                slot_id, slot_num, content_preview, last_sent, interval = slot
                print(f"  Slot {slot_num} (ID: {slot_id}): {content_preview[:30]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking admin slot 2: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ADMIN SLOT 2 DIAGNOSTIC TOOL")
    print("=" * 60)
    check_admin_slot_2()
    print("\n" + "=" * 60)
