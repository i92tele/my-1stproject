#!/usr/bin/env python3
"""
Check Ads With Destinations

This script checks for ad slots and their destinations.

Usage:
    python check_ads_with_destinations.py
"""

import sqlite3
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def main():
    print("🔍 Checking for ad slots and their destinations...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all ad slots
        cursor.execute("""
            SELECT 
                id, 
                user_id, 
                content,
                interval_minutes,
                last_sent_at,
                is_paused
            FROM 
                ad_slots
            ORDER BY 
                last_sent_at ASC NULLS FIRST
        """)
        
        ad_slots = cursor.fetchall()
        
        if not ad_slots:
            print("No ad slots found in the system.")
            return
        
        print(f"Found {len(ad_slots)} total ad slots:")
        
        # Calculate current time
        now = datetime.now()
        
        # Process each ad slot
        for slot in ad_slots:
            slot_id = slot['id']
            user_id = slot['user_id']
            content = slot['content']
            interval_minutes = slot['interval_minutes']
            last_sent = slot['last_sent_at'] if slot['last_sent_at'] else "Never"
            is_paused = slot['is_paused'] == 1 if slot['is_paused'] is not None else False
            
            # Get destinations for this slot
            cursor.execute("""
                SELECT 
                    destination_id, 
                    destination_name,
                    is_active
                FROM 
                    slot_destinations
                WHERE 
                    slot_id = ?
            """, (slot_id,))
            
            destinations = cursor.fetchall()
            
            # Calculate next posting time
            status = "PAUSED" if is_paused else ""
            next_post = ""
            
            if not is_paused and last_sent != "Never" and interval_minutes:
                try:
                    last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S')
                    next_post_dt = last_sent_dt + timedelta(minutes=interval_minutes)
                    next_post = next_post_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Check if it's due
                    if next_post_dt <= now:
                        status = "DUE NOW"
                    else:
                        minutes_until = (next_post_dt - now).total_seconds() / 60
                        if minutes_until <= 60:
                            status = "DUE SOON"
                except Exception as e:
                    status = f"ERROR: {e}"
            elif not is_paused and last_sent == "Never":
                status = "NEW"
            
            # Print slot info
            print(f"\n{'=' * 80}")
            print(f"SLOT {slot_id} | User: {user_id} | Status: {status}")
            print(f"Last sent: {last_sent} | Interval: {interval_minutes} minutes")
            if next_post:
                print(f"Next post: {next_post}")
            
            # Print content preview
            if content:
                preview = content[:100] + "..." if len(content) > 100 else content
                print(f"\nContent: {preview}")
            
            # Print destinations
            print(f"\nDestinations ({len(destinations)}):")
            if destinations:
                print(f"{'ID':<30} | {'Name':<30} | {'Status'}")
                print("-" * 80)
                for dest in destinations:
                    dest_id = dest['destination_id']
                    dest_name = dest['destination_name'] or "Unknown"
                    is_active = "Active" if dest['is_active'] == 1 else "Inactive"
                    print(f"{dest_id:<30} | {dest_name:<30} | {is_active}")
            else:
                print("No destinations found for this slot")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking ads: {e}")

if __name__ == "__main__":
    main()
