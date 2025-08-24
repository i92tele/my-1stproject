#!/usr/bin/env python3
"""
Fix Admin Slot Destinations

This script fixes the issue where admin slots can't find their destinations
"""

import asyncio
import sys
import logging
import sqlite3
import json
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_admin_destinations():
    """Fix admin slot destinations by creating the missing table and migrating data."""
    try:
        print("🔧 Fixing admin slot destinations...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Create admin_slot_destinations table if it doesn't exist
        print("📍 Creating admin_slot_destinations table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_slot_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER,
                destination_type TEXT DEFAULT 'group',
                destination_id TEXT,
                destination_name TEXT,
                alias TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES admin_ad_slots(id)
            )
        ''')
        
        # 2. Check if admin_slot_destinations table is empty
        cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📍 Migrating destinations from admin_ad_slots JSON...")
            
            # Get all admin slots with destinations
            cursor.execute("SELECT id, destinations FROM admin_ad_slots WHERE destinations IS NOT NULL AND destinations != '[]'")
            admin_slots = cursor.fetchall()
            
            migrated_count = 0
            for slot_id, destinations_json in admin_slots:
                try:
                    destinations = json.loads(destinations_json)
                    for dest in destinations:
                        cursor.execute('''
                            INSERT INTO admin_slot_destinations 
                            (slot_id, destination_type, destination_id, destination_name, alias, is_active)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            slot_id,
                            dest.get('destination_type', 'group'),
                            dest.get('destination_id', ''),
                            dest.get('destination_name', ''),
                            dest.get('alias'),
                            1
                        ))
                        migrated_count += 1
                    print(f"✅ Migrated {len(destinations)} destinations for admin slot {slot_id}")
                except Exception as e:
                    print(f"❌ Error migrating destinations for slot {slot_id}: {e}")
            
            print(f"✅ Total destinations migrated: {migrated_count}")
        else:
            print(f"✅ admin_slot_destinations table already has {count} records")
        
        # 3. Test the fix
        print("📍 Testing admin slot destinations...")
        cursor.execute("SELECT id FROM admin_ad_slots WHERE is_active = 1 LIMIT 1")
        test_slot = cursor.fetchone()
        
        if test_slot:
            slot_id = test_slot[0]
            cursor.execute("SELECT COUNT(*) FROM admin_slot_destinations WHERE slot_id = ? AND is_active = 1", (slot_id,))
            dest_count = cursor.fetchone()[0]
            print(f"✅ Admin slot {slot_id} has {dest_count} destinations")
        else:
            print("⚠️ No active admin slots found for testing")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # 4. Test with database manager
        print("📍 Testing database manager get_slot_destinations...")
        try:
            if test_slot:
                destinations = await db.get_slot_destinations(slot_id, 'admin')
                print(f"✅ Database manager found {len(destinations)} destinations for admin slot {slot_id}")
                
                if destinations:
                    for dest in destinations[:3]:  # Show first 3
                        print(f"  • {dest.get('destination_name', 'Unknown')} ({dest.get('destination_id', 'No ID')})")
                else:
                    print("❌ No destinations found - this is the problem!")
            else:
                print("⚠️ No test slot available")
        except Exception as e:
            print(f"❌ Error testing database manager: {e}")
        
        print("\n✅ Admin destinations fix completed!")
        print("🔄 Restart your bot to apply the fix")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing admin destinations: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("ADMIN DESTINATIONS FIX")
    print("=" * 80)
    
    success = asyncio.run(fix_admin_destinations())
    
    if success:
        print("\n✅ Admin destinations fix completed successfully!")
    else:
        print("\n❌ Admin destinations fix failed!")
    
    sys.exit(0 if success else 1)
