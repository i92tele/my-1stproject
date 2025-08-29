#!/usr/bin/env python3
"""
Check All Due Slots
Find which slots are actually due for posting
"""

import asyncio
import sys
import os
import sqlite3
import logging
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database.manager import DatabaseManager
from config import BotConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_all_due_slots():
    """Check all slots and find which ones are actually due."""
    print("🔍 Checking All Due Slots")
    print("=" * 50)
    
    try:
        # Initialize database
        config = BotConfig()
        db_path = "bot_database.db"
        db = DatabaseManager(db_path, logger)
        await db.initialize()
        
        # Connect directly to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("\n1️⃣ All Active Slots with Due Times:")
        print("-" * 50)
        
        # Get all active slots with their due times
        cursor.execute("""
            SELECT 
                s.id,
                s.user_id,
                u.username,
                s.is_active,
                s.content,
                s.last_sent_at,
                s.interval_minutes,
                u.subscription_expires,
                datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes') as due_time,
                datetime('now') as current_time,
                CASE 
                    WHEN s.last_sent_at IS NULL THEN 1
                    WHEN datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes') THEN 1
                    ELSE 0
                END as is_due
            FROM ad_slots s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
            ORDER BY s.id
        """)
        
        slots = cursor.fetchall()
        
        if not slots:
            print("❌ No active slots found!")
            return
        
        due_slots = []
        not_due_slots = []
        
        for slot in slots:
            slot_id = slot['id']
            username = slot['username']
            last_sent = slot['last_sent_at']
            interval = slot['interval_minutes']
            due_time = slot['due_time']
            current_time = slot['current_time']
            is_due = slot['is_due']
            
            if is_due:
                due_slots.append(slot)
                status = "🟢 DUE"
            else:
                not_due_slots.append(slot)
                status = "🟡 NOT DUE"
            
            print(f"📋 Slot {slot_id} ({username}): {status}")
            print(f"   Last Sent: {last_sent or 'Never'}")
            print(f"   Interval: {interval} minutes")
            print(f"   Due Time: {due_time or 'Immediate'}")
            print(f"   Current: {current_time}")
            
            if last_sent and due_time:
                # Calculate time until due
                try:
                    due_dt = datetime.fromisoformat(due_time.replace('Z', '+00:00'))
                    current_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
                    time_until_due = due_dt - current_dt
                    
                    if time_until_due.total_seconds() > 0:
                        hours = int(time_until_due.total_seconds() // 3600)
                        minutes = int((time_until_due.total_seconds() % 3600) // 60)
                        print(f"   Time until due: {hours}h {minutes}m")
                    else:
                        overdue_minutes = abs(int(time_until_due.total_seconds() // 60))
                        print(f"   ⚠️  Overdue by: {overdue_minutes}m")
                except:
                    print(f"   ⚠️  Time calculation error")
            
            print()
        
        print("\n2️⃣ Summary:")
        print("-" * 30)
        print(f"🟢 Due slots: {len(due_slots)}")
        print(f"🟡 Not due slots: {len(not_due_slots)}")
        print(f"📊 Total active slots: {len(slots)}")
        
        if due_slots:
            print(f"\n3️⃣ Slots That SHOULD Be Posted:")
            print("-" * 40)
            for slot in due_slots:
                print(f"   📋 Slot {slot['id']} ({slot['username']})")
        
        if not_due_slots:
            print(f"\n4️⃣ Slots Waiting:")
            print("-" * 30)
            for slot in not_due_slots:
                slot_id = slot['id']
                username = slot['username']
                last_sent = slot['last_sent_at']
                interval = slot['interval_minutes']
                due_time = slot['due_time']
                
                if last_sent and due_time:
                    try:
                        due_dt = datetime.fromisoformat(due_time.replace('Z', '+00:00'))
                        current_dt = datetime.fromisoformat(slot['current_time'].replace('Z', '+00:00'))
                        time_until_due = due_dt - current_dt
                        
                        if time_until_due.total_seconds() > 0:
                            hours = int(time_until_due.total_seconds() // 3600)
                            minutes = int((time_until_due.total_seconds() % 3600) // 60)
                            print(f"   📋 Slot {slot_id} ({username}): {hours}h {minutes}m until due")
                    except:
                        print(f"   📋 Slot {slot_id} ({username}): Time calculation error")
        
        print(f"\n5️⃣ Testing get_active_ads_to_send():")
        print("-" * 40)
        
        # Test the actual method
        active_ads = await db.get_active_ads_to_send()
        print(f"   Method returned {len(active_ads)} slots")
        
        if active_ads:
            print(f"   Slots returned by method:")
            for ad in active_ads:
                print(f"      - Slot {ad.get('id')} ({ad.get('username', 'Unknown')})")
        else:
            print(f"   ❌ No slots returned by method")
        
        # Check if the method matches our manual calculation
        method_slot_ids = [ad.get('id') for ad in active_ads]
        manual_due_ids = [slot['id'] for slot in due_slots]
        
        if set(method_slot_ids) == set(manual_due_ids):
            print(f"   ✅ Method matches manual calculation")
        else:
            print(f"   ❌ Method does NOT match manual calculation")
            print(f"      Manual due: {manual_due_ids}")
            print(f"      Method returned: {method_slot_ids}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error during check: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_all_due_slots())
