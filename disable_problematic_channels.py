#!/usr/bin/env python3
"""
Disable Problematic Channels
Disable channels that require multiple step access, captcha, or have permission issues
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def disable_problematic_channels():
    """Disable problematic channels based on analysis results."""
    print("🚫 DISABLING PROBLEMATIC CHANNELS")
    print("=" * 50)
    
    # Problematic channels identified from analysis
    problematic_channels = [
        # High error count channels
        "@impacting",           # 10 permission denied errors
        "@sectormarket/109",    # 8 entity not found errors
        "@social",              # 5 invalid destination errors
        "@sectormarket/20",     # 2 entity not found errors
        "@sectormarket/10",     # 2 entity not found errors
        "@sectormarket",        # 2 permission denied errors
        
        # Rate limited channels
        "@instaempiremarket",   # 4 rate limit errors
        
        # Invalid destination formats
        "@c/2256623070",        # Invalid destination
        "@social/68316",        # Invalid destination
        "@social/16",           # Invalid destination
        "@MafiaMarketss/26",    # Invalid destination
        "@social/17",           # Invalid destination
        
        # Other problematic channels
        "@memermarket",         # 4 permission denied errors
        "@MarketPlace_666",     # 4 permission denied errors
    ]
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        print(f"\n📋 PROBLEMATIC CHANNELS TO DISABLE:")
        print("-" * 40)
        for channel in problematic_channels:
            print(f"  • {channel}")
        
        print(f"\n🔧 DISABLING CHANNELS...")
        print("-" * 25)
        
        disabled_count = 0
        not_found_count = 0
        
        for channel in problematic_channels:
            try:
                # Check if channel exists in destinations table
                cursor.execute("""
                    SELECT id, destination_id, destination_name, is_active 
                    FROM destinations 
                    WHERE destination_id = ?
                """, (channel,))
                
                result = cursor.fetchone()
                
                if result:
                    dest_id, dest_id_col, dest_name, is_active = result
                    
                    if is_active:
                        # Disable the channel
                        cursor.execute("""
                            UPDATE destinations 
                            SET is_active = 0, updated_at = ?
                            WHERE id = ?
                        """, (datetime.now(), dest_id))
                        
                        print(f"✅ Disabled: {channel} ({dest_name})")
                        disabled_count += 1
                    else:
                        print(f"⚠️ Already disabled: {channel} ({dest_name})")
                else:
                    print(f"❌ Not found: {channel}")
                    not_found_count += 1
                    
            except Exception as e:
                print(f"❌ Error disabling {channel}: {e}")
        
        # Commit changes
        conn.commit()
        
        print(f"\n📊 DISABLING RESULTS:")
        print("-" * 25)
        print(f"  • Disabled: {disabled_count} channels")
        print(f"  • Already disabled: {len(problematic_channels) - disabled_count - not_found_count} channels")
        print(f"  • Not found: {not_found_count} channels")
        
        # Show remaining active channels
        print(f"\n✅ REMAINING ACTIVE CHANNELS:")
        print("-" * 30)
        
        cursor.execute("""
            SELECT destination_id, destination_name 
            FROM destinations 
            WHERE is_active = 1
            ORDER BY destination_id
        """)
        
        active_channels = cursor.fetchall()
        if active_channels:
            for dest_id, dest_name in active_channels:
                print(f"  • {dest_id} ({dest_name})")
        else:
            print("  No active channels remaining")
        
        # Create a backup of disabled channels
        print(f"\n💾 CREATING BACKUP...")
        print("-" * 20)
        
        backup_file = f"disabled_channels_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(backup_file, 'w') as f:
            f.write("DISABLED CHANNELS BACKUP\n")
            f.write("=" * 30 + "\n")
            f.write(f"Date: {datetime.now()}\n\n")
            f.write("Problematic channels that were disabled:\n")
            for channel in problematic_channels:
                f.write(f"  • {channel}\n")
            f.write(f"\nTotal disabled: {disabled_count}\n")
        
        print(f"✅ Backup created: {backup_file}")
        
        # Show impact on ad slots
        print(f"\n📊 IMPACT ON AD SLOTS:")
        print("-" * 25)
        
        cursor.execute("""
            SELECT 
                s.id, s.slot_type, COUNT(sd.destination_id) as total_destinations,
                SUM(CASE WHEN d.is_active = 1 THEN 1 ELSE 0 END) as active_destinations
            FROM (
                SELECT id, 'user' as slot_type FROM ad_slots WHERE is_active = 1
                UNION ALL
                SELECT id, 'admin' as slot_type FROM admin_ad_slots WHERE is_active = 1
            ) s
            LEFT JOIN slot_destinations sd ON s.id = sd.slot_id
            LEFT JOIN destinations d ON sd.destination_id = d.id
            GROUP BY s.id, s.slot_type
            ORDER BY s.slot_type, s.id
        """)
        
        slot_impact = cursor.fetchall()
        if slot_impact:
            for slot_id, slot_type, total_dest, active_dest in slot_impact:
                print(f"  {slot_type.upper()} Slot {slot_id}: {active_dest}/{total_dest} destinations active")
        else:
            print("  No active ad slots found")
        
        conn.close()
        
        print(f"\n🎉 CHANNEL DISABLING COMPLETE!")
        print(f"\n📋 SUMMARY:")
        print(f"  • Disabled {disabled_count} problematic channels")
        print(f"  • {len(active_channels)} channels remain active")
        print(f"  • Backup saved to {backup_file}")
        print(f"\n🚀 Your bot should now focus on working channels only!")
        
    except Exception as e:
        print(f"❌ Error during channel disabling: {e}")
        import traceback
        traceback.print_exc()

def create_channel_blacklist():
    """Create a permanent blacklist for problematic channels."""
    print(f"\n🛡️ CREATING CHANNEL BLACKLIST")
    print("-" * 30)
    
    blacklist_channels = [
        # Channels requiring multiple step access
        "@impacting",
        "@sectormarket/109",
        "@sectormarket/20", 
        "@sectormarket/10",
        
        # Channels with captcha or verification
        "@social",
        "@social/68316",
        "@social/16",
        "@social/17",
        
        # Invalid or non-existent channels
        "@c/2256623070",
        "@MafiaMarketss/26",
        
        # Rate-limited channels (temporary)
        "@instaempiremarket",
        
        # Permission denied channels
        "@memermarket",
        "@MarketPlace_666",
    ]
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Create blacklist table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_id TEXT UNIQUE NOT NULL,
                reason TEXT,
                blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_permanent BOOLEAN DEFAULT 1
            )
        ''')
        
        # Add channels to blacklist
        added_count = 0
        for channel in blacklist_channels:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO channel_blacklist (destination_id, reason)
                    VALUES (?, ?)
                ''', (channel, "Multiple step access, captcha, or permission issues"))
                
                if cursor.rowcount > 0:
                    print(f"✅ Added to blacklist: {channel}")
                    added_count += 1
                else:
                    print(f"⚠️ Already blacklisted: {channel}")
                    
            except Exception as e:
                print(f"❌ Error adding {channel} to blacklist: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 BLACKLIST RESULTS:")
        print(f"  • Added {added_count} channels to blacklist")
        print(f"  • Blacklist prevents future activation of these channels")
        
    except Exception as e:
        print(f"❌ Error creating blacklist: {e}")

async def main():
    """Main function."""
    print("🚫 CHANNEL MANAGEMENT TOOL")
    print("=" * 50)
    
    # Disable problematic channels
    await disable_problematic_channels()
    
    # Create permanent blacklist
    create_channel_blacklist()
    
    print(f"\n🎯 NEXT STEPS:")
    print("=" * 15)
    print("1. Monitor logs for improved success rate")
    print("2. Focus on remaining active channels")
    print("3. Consider re-enabling rate-limited channels later")
    print("4. Add new high-quality channels to replace disabled ones")

if __name__ == "__main__":
    asyncio.run(main())
