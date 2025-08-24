#!/usr/bin/env python3
"""
Check Ads Script (Schema-Adaptive)

This script checks for any ad slots that are due for posting,
adapting to the actual database schema.

Usage:
    python check_ads_adaptive.py
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
    print("🔍 Checking for ad slots...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query based on actual schema

        query = """
        SELECT 
            id, 
            user_id, 
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
        
        # Display results
        print(f"Found {len(results)} total ad slots:")
        print("\n{:<5} {:<10}".format("ID", "User"), end="")
        print(" {:<20}".format("Last Sent"), end="")
        print(" {:<15} {:<10}".format("Destinations", "Status"))
        print("-" * 80)
        
        # Calculate current time
        now = datetime.now()
        
        for row in results:
            slot_id = row['id']
            user_id = row['user_id']
            slot_type = 'unknown'
            frequency = None
            last_sent = row['last_sent_at'] if row['last_sent_at'] else "Never"
            is_paused = row['is_paused'] == 1 if 'is_paused' in row.keys() else False
            destination_count = row['destination_count']
            
            # Calculate status
            status = "PAUSED" if is_paused else ""

            print("{:<5} {:<10}".format(slot_id, f"ID:{user_id}"), end="")
            print(" {:<20}".format(last_sent[:19] if last_sent != "Never" else "Never"), end="")
            print(" {:<15} {:<10}".format(f"{destination_count} dests", status))
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking ads: {e}")

if __name__ == "__main__":
    main()
