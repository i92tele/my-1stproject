#!/usr/bin/env python3
"""
Check Ads Script (Fixed)
Shows ads that are due for posting with proper table detection

Usage:
    python check_ads_fixed.py
"""

import sqlite3
from datetime import datetime, timedelta

# Database path
DATABASE_PATH = "bot_database.db"

def main():
    print("🔍 Checking for due ad slots...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ad_slots'")
        has_ad_slots = cursor.fetchone() is not None
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destinations'")
        has_destinations = cursor.fetchone() is not None
        
        if not has_ad_slots:
            print("❌ Error: 'ad_slots' table does not exist in the database")
            return
            
        # Get all active ad slots (with or without destinations table)
        if has_destinations:
            query = """
            SELECT 
                a.id, 
                a.user_id, 
                a.slot_type, 
                a.frequency_hours, 
                a.last_sent_at,
                a.is_paused,
                COUNT(d.id) as destination_count
            FROM 
                ad_slots a
            LEFT JOIN 
                destinations d ON a.id = d.slot_id
            GROUP BY 
                a.id
            ORDER BY 
                a.last_sent_at ASC
            """
        else:
            # Fallback query without destinations
            query = """
            SELECT 
                id, 
                user_id, 
                slot_type, 
                frequency_hours, 
                last_sent_at,
                is_paused,
                0 as destination_count
            FROM 
                ad_slots
            ORDER BY 
                last_sent_at ASC
            """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No ad slots found in the system.")
            return
        
        # Calculate current time
        now = datetime.now()
        
        # Display results
        print(f"Found {len(results)} total ad slots:")
        print("\n{:<5} {:<10} {:<10} {:<20} {:<10} {:<15} {:<10}".format(
            "ID", "User", "Type", "Last Sent", "Frequency", "Destinations", "Status"
        ))
        print("-" * 85)
        
        due_count = 0
        for row in results:
            slot_id = row['id']
            user_id = row['user_id']
            slot_type = row['slot_type']
            frequency = row['frequency_hours']
            last_sent = row['last_sent_at'] if row['last_sent_at'] else "Never"
            is_paused = row['is_paused'] == 1
            destination_count = row['destination_count']
            
            # Calculate next posting time
            status = "PAUSED" if is_paused else ""
            if not is_paused and last_sent != "Never" and frequency:
                last_sent_dt = datetime.strptime(last_sent, '%Y-%m-%d %H:%M:%S')
                next_post_dt = last_sent_dt + timedelta(hours=frequency)
                
                # Check if it's due
                if next_post_dt <= now:
                    status = "DUE NOW"
                    due_count += 1
                else:
                    hours_until = (next_post_dt - now).total_seconds() / 3600
                    if hours_until <= 1:
                        status = "DUE SOON"
            elif not is_paused and last_sent == "Never":
                status = "NEW"
                due_count += 1
            
            print("{:<5} {:<10} {:<10} {:<20} {:<10} {:<15} {:<10}".format(
                slot_id, 
                f"ID:{user_id}", 
                slot_type, 
                last_sent[:19] if last_sent != "Never" else "Never", 
                f"{frequency}h" if frequency else "N/A",
                f"{destination_count} dests",
                status
            ))
        
        print("\n📊 Summary:")
        print(f"Total ad slots: {len(results)}")
        print(f"Due now: {due_count}")
        
        # Check database schema for admin interface tables
        print("\n🔍 Checking database schema for admin interface tables:")
        tables_to_check = [
            'users', 'subscriptions', 'payments', 'worker_usage', 
            'worker_cooldowns', 'worker_bans', 'worker_activity_log'
        ]
        
        for table in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            exists = cursor.fetchone() is not None
            print(f"Table '{table}': {'✅ Exists' if exists else '❌ Missing'}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking ads: {e}")

if __name__ == "__main__":
    main()
