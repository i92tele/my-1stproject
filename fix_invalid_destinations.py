#!/usr/bin/env python3
"""
Fix Invalid Destinations
Fix destinations that are causing posting failures
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    print("🔧 FIXING INVALID DESTINATIONS")
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
        
        print("📋 CHECKING DESTINATION STATUS:")
        print("-" * 40)
        
        # Check admin slot destinations
        cursor.execute("""
            SELECT asd.id, asd.slot_id, asd.destination_id, asd.destination_name, asd.is_active,
                   COUNT(*) as error_count
            FROM admin_slot_destinations asd
            LEFT JOIN worker_activity_log wal ON asd.destination_id = wal.destination_id
            WHERE asd.is_active = 1
            GROUP BY asd.id, asd.slot_id, asd.destination_id, asd.destination_name, asd.is_active
            ORDER BY error_count DESC
        """)
        
        destinations = cursor.fetchall()
        
        print(f"📊 Found {len(destinations)} active destinations")
        
        # Check for problematic destinations
        problematic_destinations = []
        
        for dest in destinations:
            dest_id, slot_id, dest_id_name, dest_name, is_active, error_count = dest
            
            # Check if destination has recent errors
            cursor.execute("""
                SELECT COUNT(*) FROM worker_activity_log 
                WHERE destination_id = ? AND success = 0 
                AND created_at > datetime('now', '-1 hour')
            """, (dest_id_name,))
            
            recent_errors = cursor.fetchone()[0]
            
            if recent_errors > 0:
                problematic_destinations.append({
                    'id': dest_id,
                    'destination_id': dest_id_name,
                    'destination_name': dest_name,
                    'recent_errors': recent_errors,
                    'total_errors': error_count
                })
        
        if problematic_destinations:
            print(f"\n❌ PROBLEMATIC DESTINATIONS ({len(problematic_destinations)}):")
            print("-" * 40)
            
            for dest in problematic_destinations:
                print(f"  🚫 {dest['destination_id']} ({dest['destination_name']})")
                print(f"     - Recent errors: {dest['recent_errors']}")
                print(f"     - Total errors: {dest['total_errors']}")
            
            print(f"\n🔧 FIXING OPTIONS:")
            print("-" * 40)
            print("1. Deactivate problematic destinations")
            print("2. Check destination validity")
            print("3. Update destination information")
            
            # Ask if user wants to deactivate problematic destinations
            print(f"\n💡 RECOMMENDATION:")
            print("Deactivate destinations with many recent errors to improve posting success rate")
            
            # Deactivate destinations with high error rates
            deactivated_count = 0
            for dest in problematic_destinations:
                if dest['recent_errors'] >= 3:  # Deactivate if 3+ recent errors
                    cursor.execute("""
                        UPDATE admin_slot_destinations 
                        SET is_active = 0 
                        WHERE id = ?
                    """, (dest['id'],))
                    deactivated_count += 1
                    print(f"  ✅ Deactivated {dest['destination_id']}")
            
            if deactivated_count > 0:
                conn.commit()
                print(f"\n✅ Deactivated {deactivated_count} problematic destinations")
            else:
                print(f"\n✅ No destinations needed deactivation")
        else:
            print("✅ No problematic destinations found")
        
        # Show posting statistics
        print(f"\n📊 POSTING STATISTICS:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_posts
            FROM worker_activity_log 
            WHERE created_at > datetime('now', '-1 hour')
        """)
        
        stats = cursor.fetchone()
        if stats and stats[0] > 0:
            total, successful, failed = stats
            success_rate = (successful / total) * 100 if total > 0 else 0
            
            print(f"  📈 Total posts (last hour): {total}")
            print(f"  ✅ Successful: {successful}")
            print(f"  ❌ Failed: {failed}")
            print(f"  📊 Success rate: {success_rate:.1f}%")
            
            if success_rate < 50:
                print(f"  ⚠️ Low success rate - consider reviewing destinations")
            else:
                print(f"  ✅ Good success rate")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
