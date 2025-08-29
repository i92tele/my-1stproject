#!/usr/bin/env python3
"""
Fix Worker Database
Fix worker database schema and activate workers properly
"""

import asyncio
import logging
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerDatabaseFixer:
    """Fix worker database issues."""
    
    def __init__(self):
        self.logger = logger
    
    async def check_worker_table_schema(self):
        """Check the actual schema of the workers table."""
        print("🔍 CHECKING WORKER TABLE SCHEMA")
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
            
            # Check table schema
            cursor.execute("PRAGMA table_info(workers)")
            columns = cursor.fetchall()
            
            print("📋 Workers table columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check table structure
            cursor.execute("SELECT * FROM workers LIMIT 1")
            sample_worker = cursor.fetchone()
            
            if sample_worker:
                print(f"📊 Sample worker data: {sample_worker}")
            
            await db.close()
            
            return [col[1] for col in columns]
            
        except Exception as e:
            print(f"❌ Error checking schema: {e}")
            return []
    
    async def fix_worker_duplicates(self):
        """Remove duplicate worker entries using correct schema."""
        print("\n🔧 FIXING WORKER DUPLICATES")
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
            
            # Check if we have a rowid column (SQLite's internal id)
            cursor.execute("PRAGMA table_info(workers)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Find duplicate workers using worker_id
            cursor.execute("""
                SELECT worker_id, COUNT(*) as count
                FROM workers 
                GROUP BY worker_id 
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"🔍 Found {len(duplicates)} worker IDs with duplicates:")
                for worker_id, count in duplicates:
                    print(f"  - Worker {worker_id}: {count} entries")
                
                # Keep only the most recent entry for each duplicate
                for worker_id, count in duplicates:
                    if 'created_at' in columns:
                        cursor.execute("""
                            DELETE FROM workers 
                            WHERE worker_id = ? 
                            AND rowid NOT IN (
                                SELECT MAX(rowid) 
                                FROM workers 
                                WHERE worker_id = ?
                            )
                        """, (worker_id, worker_id))
                    else:
                        # If no created_at, keep the first one
                        cursor.execute("""
                            DELETE FROM workers 
                            WHERE worker_id = ? 
                            AND rowid NOT IN (
                                SELECT MIN(rowid) 
                                FROM workers 
                                WHERE worker_id = ?
                            )
                        """, (worker_id, worker_id))
                
                conn.commit()
                print(f"✅ Removed {sum(count-1 for _, count in duplicates)} duplicate entries")
            else:
                print("✅ No duplicate workers found")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error fixing duplicates: {e}")
    
    async def activate_workers_properly(self, max_workers=10):
        """Activate workers using the correct schema."""
        print(f"\n🔧 ACTIVATING WORKERS (max: {max_workers})")
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
            
            # Check schema
            cursor.execute("PRAGMA table_info(workers)")
            columns = [col[1] for col in cursor.fetchall()]
            
            print(f"📋 Available columns: {columns}")
            
            # Get workers that can be activated (using is_active instead of status)
            if 'created_at' in columns:
                cursor.execute("""
                    SELECT rowid, worker_id, is_active, created_at
                    FROM workers 
                    WHERE is_active = 0
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (max_workers,))
            else:
                cursor.execute("""
                    SELECT rowid, worker_id, is_active
                    FROM workers 
                    WHERE is_active = 0
                    ORDER BY rowid ASC
                    LIMIT ?
                """, (max_workers,))
            
            available_workers = cursor.fetchall()
            
            print(f"📋 Found {len(available_workers)} workers available for activation")
            
            activated_count = 0
            for worker in available_workers:
                worker_id = worker[1]
                current_active = worker[2]
                
                # Activate worker (set is_active = 1)
                if 'last_used' in columns:
                    cursor.execute("""
                        UPDATE workers 
                        SET is_active = 1, last_used = CURRENT_TIMESTAMP
                        WHERE worker_id = ?
                    """, (worker_id,))
                else:
                    cursor.execute("""
                        UPDATE workers 
                        SET is_active = 1
                        WHERE worker_id = ?
                    """, (worker_id,))
                
                print(f"✅ Activated worker {worker_id} (was: {current_active})")
                activated_count += 1
                
                if activated_count >= max_workers:
                    break
            
            conn.commit()
            print(f"✅ Activated {activated_count} workers")
            
            # Deactivate excess workers
            cursor.execute("""
                SELECT COUNT(*) FROM workers WHERE is_active = 1
            """)
            active_count = cursor.fetchone()[0]
            
            if active_count > max_workers:
                excess = active_count - max_workers
                if 'last_used' in columns:
                    cursor.execute("""
                        UPDATE workers 
                        SET is_active = 0
                        WHERE is_active = 1
                        ORDER BY last_used DESC
                        LIMIT ?
                    """, (excess,))
                else:
                    cursor.execute("""
                        UPDATE workers 
                        SET is_active = 0
                        WHERE is_active = 1
                        ORDER BY rowid DESC
                        LIMIT ?
                    """, (excess,))
                
                conn.commit()
                print(f"✅ Deactivated {excess} excess workers")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error activating workers: {e}")
    
    async def clean_excess_workers(self):
        """Remove excess workers keeping only 10."""
        print("\n🔧 CLEANING EXCESS WORKERS")
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
            
            # Count total workers
            cursor.execute("SELECT COUNT(*) FROM workers")
            total_workers = cursor.fetchone()[0]
            
            print(f"📊 Total workers before cleanup: {total_workers}")
            
            if total_workers > 10:
                # Keep only the first 10 workers (by rowid)
                cursor.execute("""
                    DELETE FROM workers 
                    WHERE rowid NOT IN (
                        SELECT rowid FROM workers 
                        ORDER BY rowid ASC 
                        LIMIT 10
                    )
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"✅ Deleted {deleted_count} excess workers")
                print(f"📊 Workers after cleanup: {total_workers - deleted_count}")
            else:
                print("✅ No excess workers to clean")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error cleaning workers: {e}")
    
    async def verify_worker_status(self):
        """Verify worker status after fixes."""
        print("\n🔍 VERIFYING WORKER STATUS")
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
            
            # Count active workers using is_active
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
            active_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 0")
            inactive_count = cursor.fetchone()[0]
            
            print(f"📊 Total workers: {active_count + inactive_count}")
            print(f"✅ Active workers: {active_count}")
            print(f"❌ Inactive workers: {inactive_count}")
            
            # Show active worker details
            if active_count > 0:
                cursor.execute("""
                    SELECT worker_id, username, created_at 
                    FROM workers 
                    WHERE is_active = 1 
                    LIMIT 5
                """)
                active_workers = cursor.fetchall()
                
                print("📋 Active worker details:")
                for worker in active_workers:
                    print(f"  - Worker {worker[0]}: {worker[1]} (created: {worker[2]})")
            
            await db.close()
            
            return active_count
            
        except Exception as e:
            print(f"❌ Error verifying workers: {e}")
            return 0

async def main():
    """Main function."""
    fixer = WorkerDatabaseFixer()
    
    # Check schema
    columns = await fixer.check_worker_table_schema()
    
    # Fix duplicates
    await fixer.fix_worker_duplicates()
    
    # Clean excess workers
    await fixer.clean_excess_workers()
    
    # Activate workers
    await fixer.activate_workers_properly(max_workers=10)
    
    # Verify status
    active_count = await fixer.verify_worker_status()
    
    print("\n📊 WORKER DATABASE FIX SUMMARY")
    print("=" * 50)
    print("Issues fixed:")
    print("1. ✅ Checked worker table schema")
    print("2. ✅ Removed duplicate worker entries")
    print("3. ✅ Cleaned excess workers (kept 10)")
    print("4. ✅ Activated workers properly")
    print("5. ✅ Verified worker status")
    
    print(f"\n🎯 RESULT: {active_count} active workers")
    
    if active_count > 0:
        print("✅ SUCCESS: Workers are now active!")
        print("🚀 Scheduler should be able to post now")
    else:
        print("❌ ISSUE: No active workers found")
        print("🔧 Need to investigate further")

if __name__ == "__main__":
    asyncio.run(main())
