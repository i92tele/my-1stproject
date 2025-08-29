#!/usr/bin/env python3
"""
Analyze Failed Posts
Analyze why there are so many failed posts
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
    print("🔍 ANALYZING FAILED POSTS")
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
        
        print("📊 RECENT POSTING ACTIVITY:")
        print("-" * 40)
        
        # Check if worker_activity_log table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='worker_activity_log'
        """)
        
        if not cursor.fetchone():
            print("❌ worker_activity_log table doesn't exist")
            print("💡 This means we can't analyze failed posts from the database")
            print("📋 Check the scheduler logs for error details")
            return
        
        # Get recent posting statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_posts,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_posts
            FROM worker_activity_log 
            WHERE created_at > datetime('now', '-2 hours')
        """)
        
        stats = cursor.fetchone()
        if stats and stats[0] > 0:
            total, successful, failed = stats
            success_rate = (successful / total) * 100 if total > 0 else 0
            
            print(f"📈 Total posts (last 2 hours): {total}")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"📊 Success rate: {success_rate:.1f}%")
        
        # Analyze failed posts by error type
        print(f"\n🔍 FAILED POSTS ANALYSIS:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT error_message, COUNT(*) as error_count
            FROM worker_activity_log 
            WHERE success = 0 AND created_at > datetime('now', '-2 hours')
            GROUP BY error_message
            ORDER BY error_count DESC
        """)
        
        error_types = cursor.fetchall()
        
        if error_types:
            print("🚫 Top error types:")
            for error_msg, count in error_types:
                print(f"  - {error_msg}: {count} times")
        else:
            print("📋 No recent failed posts in database")
        
        # Check destination status
        print(f"\n🎯 DESTINATION STATUS:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT 
                asd.destination_id,
                asd.destination_name,
                asd.is_active,
                COUNT(wal.id) as total_attempts,
                SUM(CASE WHEN wal.success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN wal.success = 0 THEN 1 ELSE 0 END) as failed
            FROM admin_slot_destinations asd
            LEFT JOIN worker_activity_log wal ON asd.destination_id = wal.destination_id
                AND wal.created_at > datetime('now', '-2 hours')
            WHERE asd.is_active = 1
            GROUP BY asd.destination_id, asd.destination_name, asd.is_active
            ORDER BY failed DESC, total_attempts DESC
        """)
        
        destinations = cursor.fetchall()
        
        print(f"📊 Active destinations: {len(destinations)}")
        
        for dest in destinations:
            dest_id, dest_name, is_active, attempts, successful, failed = dest
            success_rate = (successful / attempts * 100) if attempts > 0 else 0
            
            status = "✅" if is_active else "❌"
            print(f"  {status} {dest_id} ({dest_name})")
            print(f"     - Attempts: {attempts}, Success: {successful}, Failed: {failed}")
            print(f"     - Success rate: {success_rate:.1f}%")
            
            if failed > 0 and attempts > 0:
                # Get specific errors for this destination
                cursor.execute("""
                    SELECT error_message, COUNT(*) as count
                    FROM worker_activity_log 
                    WHERE destination_id = ? AND success = 0 
                    AND created_at > datetime('now', '-2 hours')
                    GROUP BY error_message
                    ORDER BY count DESC
                    LIMIT 3
                """, (dest_id,))
                
                errors = cursor.fetchall()
                if errors:
                    print(f"     - Top errors:")
                    for error_msg, count in errors:
                        print(f"       • {error_msg}: {count} times")
        
        # Check worker count (simple version)
        print(f"\n🤖 WORKER STATUS:")
        print("-" * 40)
        
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        print(f"📊 Active workers: {active_workers}")
        
        # Common causes of failed posts
        print(f"\n💡 COMMON CAUSES OF FAILED POSTS:")
        print("-" * 40)
        print("1. Invalid destination - Channel/group doesn't exist or bot not member")
        print("2. Rate limiting - Too many posts too quickly")
        print("3. Authentication issues - Worker credentials expired")
        print("4. Content restrictions - Message violates channel rules")
        print("5. Network issues - Temporary connection problems")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        print("-" * 40)
        
        if error_types:
            most_common_error = error_types[0][0]
            if "Invalid destination" in str(most_common_error):
                print("1. Check destination validity - verify channels/groups exist")
                print("2. Ensure bot is member of all destination channels")
                print("3. Update destination information if needed")
            elif "rate" in str(most_common_error).lower():
                print("1. Reduce posting frequency")
                print("2. Add delays between posts")
                print("3. Use more workers to distribute load")
            elif "auth" in str(most_common_error).lower():
                print("1. Check worker credentials")
                print("2. Re-authenticate workers if needed")
                print("3. Verify API keys are valid")
        
        print("4. Monitor success rates and deactivate problematic destinations")
        print("5. Check scheduler logs for detailed error messages")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
