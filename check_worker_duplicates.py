#!/usr/bin/env python3
"""
Check and Fix Worker Duplicates

This script checks for duplicate workers in the database and fixes the worker count issue.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def check_worker_duplicates():
    """Check for duplicate workers in the database."""
    logger.info("🔍 Checking for worker duplicates...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check worker_cooldowns table
        cursor.execute('''
            SELECT worker_id, COUNT(*) as count 
            FROM worker_cooldowns 
            GROUP BY worker_id 
            HAVING COUNT(*) > 1
        ''')
        
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate worker entries:")
            for worker_id, count in duplicates:
                logger.warning(f"  Worker {worker_id}: {count} entries")
            
            # Get all worker entries
            cursor.execute('SELECT * FROM worker_cooldowns ORDER BY worker_id')
            all_workers = cursor.fetchall()
            
            logger.info(f"Total worker entries: {len(all_workers)}")
            
            # Show all workers
            cursor.execute('SELECT worker_id FROM worker_cooldowns ORDER BY worker_id')
            worker_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"Worker IDs: {worker_ids}")
            
            return True
        else:
            logger.info("✅ No duplicate workers found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking worker duplicates: {e}")
        return False
    finally:
        conn.close()

def fix_worker_duplicates():
    """Fix duplicate workers by keeping only one entry per worker."""
    logger.info("🔧 Fixing worker duplicates...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Get all workers with their counts
        cursor.execute('''
            SELECT worker_id, COUNT(*) as count 
            FROM worker_cooldowns 
            GROUP BY worker_id 
            HAVING COUNT(*) > 1
        ''')
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            logger.info("✅ No duplicates to fix")
            return True
        
        # For each duplicate worker, keep only the first entry
        for worker_id, count in duplicates:
            logger.info(f"Fixing worker {worker_id} with {count} entries")
            
            # Get all entries for this worker
            cursor.execute('''
                SELECT rowid FROM worker_cooldowns 
                WHERE worker_id = ? 
                ORDER BY rowid
            ''', (worker_id,))
            
            entries = cursor.fetchall()
            
            # Keep the first entry, delete the rest
            for entry in entries[1:]:
                cursor.execute('DELETE FROM worker_cooldowns WHERE rowid = ?', (entry[0],))
                logger.info(f"  Deleted duplicate entry {entry[0]}")
        
        conn.commit()
        logger.info("✅ Worker duplicates fixed")
        
        # Verify the fix
        cursor.execute('SELECT COUNT(*) FROM worker_cooldowns')
        total_workers = cursor.fetchone()[0]
        logger.info(f"Total workers after fix: {total_workers}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker duplicates: {e}")
        return False
    finally:
        conn.close()

def verify_worker_count():
    """Verify the worker count is correct."""
    logger.info("🔍 Verifying worker count...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Count total workers
        cursor.execute('SELECT COUNT(*) FROM worker_cooldowns')
        total_workers = cursor.fetchone()[0]
        
        # Count active workers
        cursor.execute('SELECT COUNT(*) FROM worker_cooldowns WHERE is_active = 1')
        active_workers = cursor.fetchone()[0]
        
        # Get unique worker IDs
        cursor.execute('SELECT DISTINCT worker_id FROM worker_cooldowns ORDER BY worker_id')
        unique_workers = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Total worker entries: {total_workers}")
        logger.info(f"Active workers: {active_workers}")
        logger.info(f"Unique worker IDs: {unique_workers}")
        logger.info(f"Unique worker count: {len(unique_workers)}")
        
        if total_workers == len(unique_workers):
            logger.info("✅ Worker count is correct")
        else:
            logger.warning(f"⚠️ Worker count mismatch: {total_workers} entries vs {len(unique_workers)} unique workers")
        
        return len(unique_workers)
        
    except Exception as e:
        logger.error(f"❌ Error verifying worker count: {e}")
        return 0
    finally:
        conn.close()

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🔧 WORKER DUPLICATE CHECK & FIX")
    logger.info("=" * 60)
    
    # Step 1: Check for duplicates
    has_duplicates = check_worker_duplicates()
    
    # Step 2: Verify current count
    current_count = verify_worker_count()
    
    # Step 3: Fix duplicates if needed
    if has_duplicates:
        if fix_worker_duplicates():
            logger.info("✅ Duplicates fixed successfully")
        else:
            logger.error("❌ Failed to fix duplicates")
            return
    
    # Step 4: Verify final count
    final_count = verify_worker_count()
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Final worker count: {final_count}")
    
    if final_count == 10:
        logger.info("✅ Worker count is correct (10 workers)")
    else:
        logger.warning(f"⚠️ Worker count is {final_count}, expected 10")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
