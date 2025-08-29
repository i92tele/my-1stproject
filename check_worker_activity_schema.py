#!/usr/bin/env python3
"""
Check Worker Activity Log Schema
Check the actual column names in the worker_activity_log table
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
    print("🔍 CHECKING WORKER ACTIVITY LOG SCHEMA")
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
        
        # Check if worker_activity_log table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='worker_activity_log'
        """)
        
        if not cursor.fetchone():
            print("❌ worker_activity_log table doesn't exist")
            return
        
        print("✅ worker_activity_log table exists")
        
        # Get table schema
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        
        print(f"\n📋 WORKER_ACTIVITY_LOG TABLE SCHEMA:")
        print("-" * 40)
        print("Column ID | Column Name | Type | Not Null | Default | Primary Key")
        print("-" * 70)
        
        for col in columns:
            col_id, name, type_name, not_null, default_val, primary_key = col
            print(f"{col_id:9} | {name:12} | {type_name:8} | {not_null:8} | {str(default_val):7} | {primary_key:11}")
        
        # Get sample data to see actual column names
        cursor.execute("SELECT * FROM worker_activity_log LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print(f"\n📊 SAMPLE DATA COLUMNS:")
            print("-" * 40)
            for i, col in enumerate(columns):
                print(f"{col[1]}: {sample[i]}")
        
        # Check for worker-related columns
        print(f"\n🔍 WORKER-RELATED COLUMNS:")
        print("-" * 40)
        worker_columns = [col for col in columns if 'worker' in col[1].lower() or 'phone' in col[1].lower()]
        
        if worker_columns:
            for col in worker_columns:
                print(f"✅ Found: {col[1]} ({col[2]})")
        else:
            print("❌ No worker-related columns found")
        
        # Check for destination-related columns
        print(f"\n🎯 DESTINATION-RELATED COLUMNS:")
        print("-" * 40)
        dest_columns = [col for col in columns if 'destination' in col[1].lower()]
        
        if dest_columns:
            for col in dest_columns:
                print(f"✅ Found: {col[1]} ({col[2]})")
        else:
            print("❌ No destination-related columns found")
        
        # Check for error-related columns
        print(f"\n🚫 ERROR-RELATED COLUMNS:")
        print("-" * 40)
        error_columns = [col for col in columns if 'error' in col[1].lower()]
        
        if error_columns:
            for col in error_columns:
                print(f"✅ Found: {col[1]} ({col[2]})")
        else:
            print("❌ No error-related columns found")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
