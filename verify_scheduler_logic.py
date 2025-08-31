#!/usr/bin/env python3
"""
Verify Scheduler Logic
Comprehensive verification of scheduler posting logic for admin and user ads
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_scheduler_logic():
    """Verify that the scheduler is correctly posting both admin and user ads."""
    print("🔍 VERIFYING SCHEDULER LOGIC")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        print("\n📊 DATABASE STATUS:")
        print("-" * 30)
        
        # Check if required tables exist
        required_tables = ['ad_slots', 'admin_ad_slots', 'users', 'destinations', 'slot_destinations']
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone():
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")
        
        print("\n👥 USER AD SLOTS:")
        print("-" * 20)
        
        # Check user ad slots
        cursor.execute("""
            SELECT 
                s.id, s.user_id, s.content, s.is_active, s.interval_minutes,
                s.last_sent_at, u.username, u.subscription_expires,
                COUNT(d.id) as destination_count
            FROM ad_slots s
            LEFT JOIN users u ON s.user_id = u.user_id
            LEFT JOIN slot_destinations d ON s.id = d.slot_id
            GROUP BY s.id
            ORDER BY s.id
        """)
        
        user_slots = cursor.fetchall()
        if user_slots:
            for slot in user_slots:
                slot_id, user_id, content, is_active, interval, last_sent, username, sub_expires, dest_count = slot
                print(f"  Slot {slot_id}: User {user_id} ({username})")
                print(f"    Active: {is_active}, Destinations: {dest_count}")
                print(f"    Interval: {interval} minutes, Last sent: {last_sent}")
                print(f"    Subscription expires: {sub_expires}")
                print(f"    Content length: {len(content) if content else 0} chars")
                
                # Check if due for posting
                if is_active and content:
                    if last_sent is None:
                        print(f"    Status: DUE (never sent)")
                    else:
                        last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                        due_time = last_sent_dt + timedelta(minutes=interval)
                        if datetime.now() >= due_time:
                            print(f"    Status: DUE (interval passed)")
                        else:
                            print(f"    Status: NOT DUE (due at {due_time})")
                else:
                    print(f"    Status: INACTIVE or NO CONTENT")
                print()
        else:
            print("  No user ad slots found")
        
        print("\n👑 ADMIN AD SLOTS:")
        print("-" * 20)
        
        # Check admin ad slots
        cursor.execute("""
            SELECT 
                s.id, s.content, s.is_active, s.interval_minutes,
                s.last_sent_at, COUNT(d.id) as destination_count
            FROM admin_ad_slots s
            LEFT JOIN slot_destinations d ON s.id = d.slot_id
            GROUP BY s.id
            ORDER BY s.id
        """)
        
        admin_slots = cursor.fetchall()
        if admin_slots:
            for slot in admin_slots:
                slot_id, content, is_active, interval, last_sent, dest_count = slot
                print(f"  Admin Slot {slot_id}:")
                print(f"    Active: {is_active}, Destinations: {dest_count}")
                print(f"    Interval: {interval} minutes, Last sent: {last_sent}")
                print(f"    Content length: {len(content) if content else 0} chars")
                
                # Check if due for posting
                if is_active and content:
                    if last_sent is None:
                        print(f"    Status: DUE (never sent)")
                    else:
                        last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                        due_time = last_sent_dt + timedelta(minutes=interval)
                        if datetime.now() >= due_time:
                            print(f"    Status: DUE (interval passed)")
                        else:
                            print(f"    Status: NOT DUE (due at {due_time})")
                else:
                    print(f"    Status: INACTIVE or NO CONTENT")
                print()
        else:
            print("  No admin ad slots found")
        
        print("\n🎯 DESTINATIONS:")
        print("-" * 15)
        
        # Check destinations
        cursor.execute("""
            SELECT 
                d.id, d.destination_id, d.destination_name, d.is_active,
                COUNT(sd.slot_id) as slot_count
            FROM destinations d
            LEFT JOIN slot_destinations sd ON d.id = sd.destination_id
            GROUP BY d.id
            ORDER BY d.destination_id
        """)
        
        destinations = cursor.fetchall()
        if destinations:
            for dest in destinations:
                dest_id, dest_name, dest_title, is_active, slot_count = dest
                print(f"  {dest_name} ({dest_title}): {slot_count} slots, Active: {is_active}")
        else:
            print("  No destinations found")
        
        print("\n🔧 SCHEDULER LOGIC VERIFICATION:")
        print("-" * 35)
        
        # Test the get_active_ads_to_send method
        try:
            active_ads = await db.get_active_ads_to_send()
            print(f"✅ get_active_ads_to_send() returned {len(active_ads)} ads")
            
            if active_ads:
                print("\n📋 ACTIVE ADS DUE FOR POSTING:")
                for ad in active_ads:
                    slot_type = ad.get('slot_type', 'unknown')
                    slot_id = ad.get('id', 'unknown')
                    username = ad.get('username', 'unknown')
                    interval = ad.get('interval_minutes', 'unknown')
                    last_sent = ad.get('last_sent_at', 'never')
                    
                    print(f"  {slot_type.upper()} Slot {slot_id}: {username}")
                    print(f"    Interval: {interval} minutes, Last sent: {last_sent}")
            else:
                print("  No ads currently due for posting")
                
        except Exception as e:
            print(f"❌ Error testing get_active_ads_to_send(): {e}")
        
        print("\n📊 WORKER STATUS:")
        print("-" * 15)
        
        # Check workers
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        print(f"Active workers: {active_workers}")
        
        cursor.execute("SELECT COUNT(*) FROM worker_cooldowns WHERE is_active = 1")
        available_workers = cursor.fetchone()[0]
        print(f"Available workers (not in cooldown): {available_workers}")
        
        print("\n🎉 SCHEDULER LOGIC VERIFICATION COMPLETE!")
        print("\n📋 SUMMARY:")
        print(f"  • User slots: {len(user_slots)}")
        print(f"  • Admin slots: {len(admin_slots)}")
        print(f"  • Destinations: {len(destinations)}")
        print(f"  • Active ads due: {len(active_ads) if 'active_ads' in locals() else 'unknown'}")
        print(f"  • Available workers: {available_workers}")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_scheduler_logic())
