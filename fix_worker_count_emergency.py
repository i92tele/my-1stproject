#!/usr/bin/env python3
"""
Emergency Worker Count Fix

This script fixes the excessive worker count (149 workers) that might be causing
performance issues and freezing problems.
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_current_workers():
    """Check the current number of workers in the database."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Count total workers
        cursor.execute("SELECT COUNT(*) FROM workers")
        total_workers = cursor.fetchone()[0]
        
        # Count active workers
        cursor.execute("SELECT COUNT(*) FROM workers WHERE is_active = 1")
        active_workers = cursor.fetchone()[0]
        
        # Get some sample worker IDs
        cursor.execute("SELECT worker_id, is_active FROM workers LIMIT 10")
        sample_workers = cursor.fetchall()
        
        conn.close()
        
        logger.info(f"📊 Current Worker Status:")
        logger.info(f"• Total workers: {total_workers}")
        logger.info(f"• Active workers: {active_workers}")
        logger.info(f"• Sample workers: {sample_workers}")
        
        return total_workers, active_workers
        
    except Exception as e:
        logger.error(f"❌ Error checking workers: {e}")
        return None, None

def fix_worker_count():
    """Fix the worker count to exactly 10 workers."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM workers")
        current_count = cursor.fetchone()[0]
        
        logger.info(f"🔍 Current worker count: {current_count}")
        
        if current_count == 10:
            logger.info("✅ Worker count is already correct (10 workers)")
            conn.close()
            return True
        
        if current_count > 10:
            logger.info(f"🔧 Reducing worker count from {current_count} to 10...")
            
            # Keep only the first 10 workers
            cursor.execute("DELETE FROM workers WHERE worker_id > 10")
            deleted_count = cursor.rowcount
            
            logger.info(f"✅ Deleted {deleted_count} excess workers")
            
        elif current_count < 10:
            logger.info(f"🔧 Increasing worker count from {current_count} to 10...")
            
            # Add missing workers
            for i in range(current_count + 1, 11):
                cursor.execute("""
                    INSERT INTO workers (worker_id, is_active, last_used_at, hourly_posts, daily_posts, safety_score)
                    VALUES (?, 1, datetime('now'), 0, 0, 100.0)
                """, (i,))
            
            added_count = 10 - current_count
            logger.info(f"✅ Added {added_count} missing workers")
        
        # Verify the fix
        cursor.execute("SELECT COUNT(*) FROM workers")
        final_count = cursor.fetchone()[0]
        
        # Ensure all workers are active
        cursor.execute("UPDATE workers SET is_active = 1")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Worker count fixed: {final_count} workers")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker count: {e}")
        return False

def verify_worker_table():
    """Verify the worker table structure."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(workers)")
        columns = cursor.fetchall()
        
        logger.info("📋 Worker table structure:")
        for col in columns:
            logger.info(f"  • {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking worker table: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚨 EMERGENCY WORKER COUNT FIX")
    logger.info("=" * 60)
    
    # Step 1: Check current status
    logger.info("Step 1: Checking current worker status...")
    total, active = check_current_workers()
    
    if total is None:
        logger.error("❌ Could not check worker status")
        return
    
    # Step 2: Verify table structure
    logger.info("\nStep 2: Verifying worker table structure...")
    if not verify_worker_table():
        logger.error("❌ Worker table structure issue")
        return
    
    # Step 3: Fix worker count
    logger.info("\nStep 3: Fixing worker count...")
    if fix_worker_count():
        logger.info("✅ Worker count fix completed")
    else:
        logger.error("❌ Worker count fix failed")
        return
    
    # Step 4: Verify fix
    logger.info("\nStep 4: Verifying fix...")
    final_total, final_active = check_current_workers()
    
    if final_total == 10:
        logger.info("✅ Worker count fix verified successfully!")
    else:
        logger.error(f"❌ Worker count fix verification failed: {final_total} workers")
        return
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Worker count fixed to exactly 10 workers")
    logger.info("✅ All workers set to active")
    logger.info("")
    logger.info("🔄 Next steps:")
    logger.info("1. Restart the bot")
    logger.info("2. Check that posting service uses only 10 workers")
    logger.info("3. Verify improved performance and no freezing")
    logger.info("4. Test admin interface functionality")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
