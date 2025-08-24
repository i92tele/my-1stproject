#!/usr/bin/env python3
"""
Check Destinations

This script checks the current destination values in the database.
"""

import sqlite3

def check_destinations():
    """Check current destination values."""
    try:
        db_path = "bot_database.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all destinations
        cursor.execute("""
            SELECT id, destination_id, destination_name 
            FROM slot_destinations 
            WHERE destination_id LIKE '%CrystalMarketss%'
        """)
        
        destinations = cursor.fetchall()
        
        print(f"Found {len(destinations)} CrystalMarketss destinations:")
        for dest_id, dest_id_str, dest_name in destinations:
            print(f"  ID: {dest_id}, Destination: '{dest_id_str}', Name: '{dest_name}'")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_destinations()
