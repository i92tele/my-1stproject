#!/usr/bin/env python3
"""
Fix Worker Database Schema

This script fixes missing columns in worker-related tables
"""

import asyncio
import sys
import logging
import sqlite3
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_worker_database():
    """Fix missing columns in worker-related tables."""
    try:
        print("🔧 Fixing worker database schema...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("\n📍 1. Checking worker_usage table...")
        
        # Check worker_usage table structure
        cursor.execute("PRAGMA table_info(worker_usage)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add missing columns to worker_usage
        missing_columns = []
        
        if 'daily_limit' not in columns:
            missing_columns.append('daily_limit')
        if 'hourly_limit' not in columns:
            missing_columns.append('hourly_limit')
        if 'created_at' not in columns:
            missing_columns.append('created_at')
        if 'updated_at' not in columns:
            missing_columns.append('updated_at')
        
        if missing_columns:
            print(f"🔧 Adding missing columns: {missing_columns}")
            for col in missing_columns:
                if col in ['daily_limit', 'hourly_limit']:
                    cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {col} INTEGER DEFAULT 150")
                else:
                    cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print(f"✅ Added column: {col}")
        else:
            print("✅ All required columns exist in worker_usage")
        
        print("\n📍 2. Checking ad_posts table...")
        
        # Check ad_posts table structure
        cursor.execute("PRAGMA table_info(ad_posts)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add missing columns to ad_posts
        if 'created_at' not in columns:
            print("🔧 Adding created_at column to ad_posts")
            cursor.execute("ALTER TABLE ad_posts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at column")
        else:
            print("✅ created_at column exists in ad_posts")
        
        print("\n📍 3. Checking worker_cooldowns table...")
        
        # Check worker_cooldowns table structure
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add missing columns to worker_cooldowns
        missing_columns = []
        
        if 'hourly_limit' not in columns:
            missing_columns.append('hourly_limit')
        if 'daily_limit' not in columns:
            missing_columns.append('daily_limit')
        if 'created_at' not in columns:
            missing_columns.append('created_at')
        if 'updated_at' not in columns:
            missing_columns.append('updated_at')
        
        if missing_columns:
            print(f"🔧 Adding missing columns: {missing_columns}")
            for col in missing_columns:
                if col in ['daily_limit', 'hourly_limit']:
                    cursor.execute(f"ALTER TABLE worker_cooldowns ADD COLUMN {col} INTEGER DEFAULT 150")
                else:
                    cursor.execute(f"ALTER TABLE worker_cooldowns ADD COLUMN {col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print(f"✅ Added column: {col}")
        else:
            print("✅ All required columns exist in worker_cooldowns")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n✅ Database schema fixes completed!")
        
        # Test the fixes
        print("\n📍 4. Testing fixes...")
        try:
            workers = await db.get_all_workers()
            available_workers = await db.get_available_workers()
            print(f"📊 Total workers: {len(workers)}")
            print(f"📊 Available workers: {len(available_workers)}")
            
            if len(workers) > 0:
                print("✅ Worker queries now work!")
            else:
                print("⚠️  No workers found (this is expected if no worker data exists)")
                
        except Exception as e:
            print(f"❌ Worker queries still failing: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing worker database: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("WORKER DATABASE FIX")
    print("=" * 80)
    
    success = asyncio.run(fix_worker_database())
    
    if success:
        print("\n✅ Worker database fix completed successfully!")
    else:
        print("\n❌ Worker database fix failed!")
    
    sys.exit(0 if success else 1)
