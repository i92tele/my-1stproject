#!/usr/bin/env python3
"""
Investigate Ad Slot Issue
Check why a specific ad slot isn't being picked up by the scheduler
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

async def investigate_ad_slot():
    """Investigate why the ad slot isn't being picked up by the scheduler."""
    print("🔍 Investigating Ad Slot Issue")
    print("=" * 50)
    
    try:
        # Initialize database
        config = BotConfig()
        db_path = "bot_database.db"  # Use the standard database path
        db = DatabaseManager(db_path, logger)
        await db.initialize()
        
        # Connect directly to database for detailed investigation
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("\n1️⃣ Checking All Ad Slots:")
        print("-" * 30)
        
        # Get all ad slots
        cursor.execute("""
            SELECT s.*, u.username, u.subscription_expires
            FROM ad_slots s
            LEFT JOIN users u ON s.user_id = u.user_id
            ORDER BY s.id DESC
        """)
        
        all_slots = cursor.fetchall()
        print(f"Total ad slots found: {len(all_slots)}")
        
        for slot in all_slots:
            slot_id = slot['id']
            user_id = slot['user_id']
            username = slot['username']
            is_active = slot['is_active']
            content = slot['content']
            last_sent = slot['last_sent_at']
            interval = slot['interval_minutes']
            subscription_expires = slot['subscription_expires']
            
            print(f"\n📋 Slot {slot_id} (User: {username}):")
            print(f"   Active: {'✅ Yes' if is_active else '❌ No'}")
            print(f"   Has Content: {'✅ Yes' if content and content.strip() else '❌ No'}")
            print(f"   Last Sent: {last_sent or 'Never'}")
            print(f"   Interval: {interval} minutes")
            print(f"   Subscription Expires: {subscription_expires or 'No expiration'}")
            
            # Check if subscription is active
            if subscription_expires:
                try:
                    expires_dt = datetime.fromisoformat(subscription_expires.replace('Z', '+00:00'))
                    is_subscription_active = datetime.now() < expires_dt
                    print(f"   Subscription Active: {'✅ Yes' if is_subscription_active else '❌ No'}")
                except:
                    print(f"   Subscription Active: ❓ Unknown (date parsing error)")
            else:
                print(f"   Subscription Active: ✅ Yes (no expiration)")
        
        print("\n2️⃣ Checking Due Calculation:")
        print("-" * 30)
        
        # Check which slots would be due according to the query
        cursor.execute("""
            SELECT s.*, u.username, 'user' as slot_type
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
            ORDER BY s.last_sent_at ASC NULLS FIRST
        """)
        
        due_slots = cursor.fetchall()
        print(f"Slots that SHOULD be due: {len(due_slots)}")
        
        for slot in due_slots:
            slot_id = slot['id']
            username = slot['username']
            last_sent = slot['last_sent_at']
            interval = slot['interval_minutes']
            
            print(f"\n📋 Due Slot {slot_id} (User: {username}):")
            if last_sent is None:
                print(f"   Reason: Never sent before")
            else:
                # Calculate when it should be due
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                    due_time = last_sent_dt + timedelta(minutes=interval)
                    now = datetime.now()
                    print(f"   Last Sent: {last_sent}")
                    print(f"   Should be due at: {due_time}")
                    print(f"   Current time: {now}")
                    print(f"   Is due: {'✅ Yes' if now >= due_time else '❌ No'}")
                except Exception as e:
                    print(f"   Error calculating due time: {e}")
        
        print("\n3️⃣ Checking Destinations:")
        print("-" * 30)
        
        # Check destinations for each slot
        for slot in all_slots:
            slot_id = slot['id']
            username = slot['username']
            
            cursor.execute("""
                SELECT COUNT(*) as dest_count
                FROM slot_destinations
                WHERE slot_id = ?
            """, (slot_id,))
            
            dest_count = cursor.fetchone()['dest_count']
            print(f"Slot {slot_id} ({username}): {dest_count} destinations")
            
            if dest_count > 0:
                cursor.execute("""
                    SELECT sd.*, d.name as destination_name
                    FROM slot_destinations sd
                    JOIN destinations d ON sd.destination_id = d.id
                    WHERE sd.slot_id = ?
                """, (slot_id,))
                
                destinations = cursor.fetchall()
                for dest in destinations[:3]:  # Show first 3
                    print(f"   - {dest['destination_name']} (ID: {dest['destination_id']})")
                if len(destinations) > 3:
                    print(f"   ... and {len(destinations) - 3} more")
        
        print("\n4️⃣ Testing get_active_ads_to_send():")
        print("-" * 30)
        
        # Test the actual method
        active_ads = await db.get_active_ads_to_send()
        print(f"get_active_ads_to_send() returned: {len(active_ads)} slots")
        
        for ad in active_ads:
            slot_id = ad.get('id')
            slot_type = ad.get('slot_type')
            username = ad.get('username')
            print(f"   - Slot {slot_id} ({slot_type}): {username}")
        
        print("\n5️⃣ Checking Scheduler Status:")
        print("-" * 30)
        
        # Check if scheduler is running
        try:
            from src.services.posting_service import PostingService
            print("✅ PostingService can be imported")
        except Exception as e:
            print(f"❌ PostingService import error: {e}")
        
        # Check worker configuration
        try:
            from scheduler.config.worker_config import WorkerConfig
            worker_config = WorkerConfig()
            workers = worker_config.load_workers_from_env()
            print(f"✅ Found {len(workers)} worker configurations")
        except Exception as e:
            print(f"❌ Worker configuration error: {e}")
        
        print("\n6️⃣ Recommendations:")
        print("-" * 30)
        
        if len(due_slots) == 0:
            print("❌ No slots are currently due for posting")
            print("   Possible reasons:")
            print("   - Slots were posted recently and haven't reached their interval")
            print("   - Slots have long intervals (e.g., 24 hours)")
            print("   - Slots are paused or inactive")
            print("   - User subscriptions have expired")
            print("   - Slots don't have content")
        else:
            print(f"✅ {len(due_slots)} slots are due for posting")
            if len(active_ads) == 0:
                print("❌ But get_active_ads_to_send() returned 0 slots")
                print("   This indicates a bug in the method")
            else:
                print(f"✅ And get_active_ads_to_send() returned {len(active_ads)} slots")
                print("   The scheduler should be processing these slots")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error during investigation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(investigate_ad_slot())
