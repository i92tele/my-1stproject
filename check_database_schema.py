#!/usr/bin/env python3
"""
Check Database Schema
Check the actual schema of all tables to understand the correct structure
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_all_tables():
    """Check schema of all tables."""
    print("🔍 CHECKING DATABASE SCHEMA")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection for direct SQL
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            print(f"  - {table_name}")
        
        print("\n" + "=" * 50)
        
        # Check each table's schema
        for table in tables:
            table_name = table[0]
            print(f"\n📋 Table: {table_name}")
            print("-" * 30)
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"  - {col_name} ({col_type}){' NOT NULL' if not_null else ''}{' PRIMARY KEY' if pk else ''}")
            
            # Show sample data
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  📊 Records: {count}")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    print(f"  📝 Sample: {sample}")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")

async def check_specific_issues():
    """Check specific issues we're trying to fix."""
    print("\n🔍 CHECKING SPECIFIC ISSUES")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        # Get connection for direct SQL
        conn = await db.get_connection()
        cursor = conn.cursor()
        
        # Check workers
        print("\n👥 WORKERS TABLE:")
        cursor.execute("SELECT COUNT(*) FROM workers")
        total_workers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        
        print(f"  - Total workers: {total_workers}")
        print(f"  - Active workers: {active_workers}")
        
        # Check ad_slots
        print("\n📝 AD_SLOTS TABLE:")
        cursor.execute("SELECT COUNT(*) FROM ad_slots")
        total_slots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        active_slots = cursor.fetchone()[0]
        
        print(f"  - Total slots: {total_slots}")
        print(f"  - Active slots: {active_slots}")
        
        # Check destinations
        print("\n🎯 DESTINATIONS TABLE:")
        try:
            cursor.execute("SELECT COUNT(*) FROM destinations")
            total_destinations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM destinations WHERE status = 'active'")
            active_destinations = cursor.fetchone()[0]
            
            print(f"  - Total destinations: {total_destinations}")
            print(f"  - Active destinations: {active_destinations}")
        except:
            print("  - Table doesn't exist")
        
        # Check subscriptions
        print("\n💳 SUBSCRIPTIONS TABLE:")
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        total_subs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active_subs = cursor.fetchone()[0]
        
        print(f"  - Total subscriptions: {total_subs}")
        print(f"  - Active subscriptions: {active_subs}")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error checking issues: {e}")

async def main():
    """Main function."""
    await check_all_tables()
    await check_specific_issues()

if __name__ == "__main__":
    asyncio.run(main())
