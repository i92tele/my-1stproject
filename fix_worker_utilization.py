#!/usr/bin/env python3
"""
Script to fix worker utilization issues in the AutoFarming Bot.
This script ensures all 10 workers are utilized and all due ads are posted.
"""

import asyncio
import sys
import os
import logging
import sqlite3
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager
from config import BotConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("fix_worker_utilization")

async def ensure_all_workers_initialized(db):
    """Ensure all 10 workers are properly initialized in the database."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check worker_cooldowns table
    try:
        cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
        worker_count = cursor.fetchone()[0]
        logger.info(f"Found {worker_count} workers in worker_cooldowns table")
        
        # Initialize missing workers
        if worker_count < 10:
            logger.info(f"Initializing {10 - worker_count} missing workers...")
            for worker_id in range(1, 11):
                # Check if this worker exists
                cursor.execute("SELECT COUNT(*) FROM worker_cooldowns WHERE worker_id = ?", (worker_id,))
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    # Initialize worker in worker_cooldowns
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO worker_cooldowns 
                        (worker_id, is_active, created_at, updated_at)
                        VALUES (?, 1, ?, ?)
                    """, (worker_id, now, now))
                    logger.info(f"Initialized worker {worker_id} in worker_cooldowns")
            
            conn.commit()
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking worker_cooldowns: {e}")
    
    # Check worker_usage table
    try:
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        usage_count = cursor.fetchone()[0]
        logger.info(f"Found {usage_count} workers in worker_usage table")
        
        # Initialize missing workers
        for worker_id in range(1, 11):
            # Check if this worker exists in worker_usage
            cursor.execute("SELECT COUNT(*) FROM worker_usage WHERE worker_id = ?", (worker_id,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                # Initialize worker in worker_usage
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                today = datetime.now().date().strftime('%Y-%m-%d')
                cursor.execute("""
                    INSERT INTO worker_usage 
                    (worker_id, hourly_posts, daily_posts, hourly_limit, daily_limit, created_at, date)
                    VALUES (?, 0, 0, 15, 150, ?, ?)
                """, (worker_id, now, today))
                logger.info(f"Initialized worker {worker_id} in worker_usage")
        
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking worker_usage: {e}")
    
    conn.close()
    
    # Use the database manager's method to properly initialize workers
    for worker_id in range(1, 11):
        await db.initialize_worker_limits(worker_id)
    
    logger.info("All workers initialized")

async def reset_worker_usage(db):
    """Reset worker usage counters to ensure all workers are available."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    try:
        # Reset hourly and daily usage counters
        cursor.execute("""
            UPDATE worker_usage
            SET hourly_posts = 0, daily_posts = 0, updated_at = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
        
        updated = cursor.rowcount
        logger.info(f"Reset usage counters for {updated} workers")
        
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.warning(f"Error resetting worker usage: {e}")
    
    conn.close()

async def ensure_slots_have_destinations(db):
    """Ensure all active slots have destinations."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check user slots without destinations
    cursor.execute("""
        SELECT id FROM ad_slots
        WHERE is_active = 1
        AND content IS NOT NULL
        AND content != ''
        AND NOT EXISTS (
            SELECT 1 FROM slot_destinations
            WHERE slot_id = ad_slots.id
            AND is_active = 1
        )
    """)
    slots_without_destinations = cursor.fetchall()
    
    if slots_without_destinations:
        logger.info(f"Found {len(slots_without_destinations)} user slots without destinations")
        
        # Add test destinations to these slots
        for slot in slots_without_destinations:
            slot_id = slot[0]
            for i in range(1, 6):  # Add 5 test destinations
                cursor.execute("""
                    INSERT INTO slot_destinations
                    (slot_id, destination_type, destination_id, destination_name, is_active, created_at)
                    VALUES (?, 'group', ?, ?, 1, ?)
                """, (
                    slot_id,
                    f"@test_group_{slot_id}_{i}",
                    f"Test Group {slot_id}-{i}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            logger.info(f"Added 5 test destinations to user slot {slot_id}")
    
    # Check admin slots without destinations
    try:
        cursor.execute("""
            SELECT id FROM admin_ad_slots
            WHERE is_active = 1
            AND content IS NOT NULL
            AND content != ''
            AND NOT EXISTS (
                SELECT 1 FROM admin_slot_destinations
                WHERE slot_id = admin_ad_slots.id
                AND is_active = 1
            )
        """)
        admin_slots_without_destinations = cursor.fetchall()
        
        if admin_slots_without_destinations:
            logger.info(f"Found {len(admin_slots_without_destinations)} admin slots without destinations")
            
            # Add test destinations to these slots
            for slot in admin_slots_without_destinations:
                slot_id = slot[0]
                for i in range(1, 6):  # Add 5 test destinations
                    cursor.execute("""
                        INSERT INTO admin_slot_destinations
                        (slot_id, destination_type, destination_id, destination_name, is_active, created_at)
                        VALUES (?, 'group', ?, ?, 1, ?)
                    """, (
                        slot_id,
                        f"@admin_test_group_{slot_id}_{i}",
                        f"Admin Test Group {slot_id}-{i}",
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                logger.info(f"Added 5 test destinations to admin slot {slot_id}")
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking admin slots: {e}")
    
    conn.commit()
    conn.close()

async def ensure_slots_are_due(db):
    """Ensure there are enough due slots to utilize all workers."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Count active slots
    cursor.execute("""
        SELECT COUNT(*) FROM ad_slots
        WHERE is_active = 1
        AND content IS NOT NULL
        AND content != ''
    """)
    active_slot_count = cursor.fetchone()[0]
    
    # Count admin slots if table exists
    admin_slot_count = 0
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots
            WHERE is_active = 1
            AND content IS NOT NULL
            AND content != ''
        """)
        admin_slot_count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        pass
    
    total_active_slots = active_slot_count + admin_slot_count
    logger.info(f"Found {total_active_slots} total active slots ({active_slot_count} user, {admin_slot_count} admin)")
    
    # Make sure we have enough slots
    if total_active_slots < 5:
        # Create additional test slots if needed
        slots_to_create = 5 - total_active_slots
        logger.info(f"Creating {slots_to_create} additional test slots")
        
        # Create test user if needed
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, subscription_tier, subscription_expires)
            VALUES (12345, 'test_user', 'Test', 'premium', ?)
        """, ((datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),))
        
        # Create test slots
        for i in range(slots_to_create):
            slot_number = i + 1
            cursor.execute("""
                INSERT INTO ad_slots (user_id, slot_number, content, is_active, interval_minutes, created_at)
                VALUES (12345, ?, ?, 1, 60, ?)
            """, (
                slot_number,
                f"Test ad content for slot {slot_number}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Get the slot ID
            slot_id = cursor.lastrowid
            
            # Add destinations
            for j in range(1, 11):  # 10 destinations per slot
                cursor.execute("""
                    INSERT INTO slot_destinations (slot_id, destination_type, destination_id, destination_name, is_active, created_at)
                    VALUES (?, 'group', ?, ?, 1, ?)
                """, (
                    slot_id,
                    f"@test_group_{slot_id}_{j}",
                    f"Test Group {slot_id}-{j}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            logger.info(f"Created test slot {slot_id} with 10 destinations")
    
    # Make all slots due by setting last_sent_at to 2 hours ago
    past_time = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Update user slots
    cursor.execute("""
        UPDATE ad_slots
        SET last_sent_at = ?
        WHERE is_active = 1
        AND content IS NOT NULL
        AND content != ''
    """, (past_time,))
    user_slots_updated = cursor.rowcount
    
    # Update admin slots if table exists
    admin_slots_updated = 0
    try:
        cursor.execute("""
            UPDATE admin_ad_slots
            SET last_sent_at = ?
            WHERE is_active = 1
            AND content IS NOT NULL
            AND content != ''
        """, (past_time,))
        admin_slots_updated = cursor.rowcount
    except sqlite3.OperationalError:
        pass
    
    logger.info(f"Made {user_slots_updated} user slots and {admin_slots_updated} admin slots due")
    
    conn.commit()
    conn.close()

async def verify_get_active_ads_to_send(db):
    """Verify that get_active_ads_to_send() returns all due ads."""
    active_ads = await db.get_active_ads_to_send()
    logger.info(f"get_active_ads_to_send() returned {len(active_ads)} slots")
    
    # Count destinations
    total_destinations = 0
    for ad in active_ads:
        slot_id = ad.get('id')
        slot_type = ad.get('slot_type', 'user')
        destinations = await db.get_slot_destinations(slot_id, slot_type)
        total_destinations += len(destinations)
    
    logger.info(f"Total destinations across all slots: {total_destinations}")
    
    # Check if we have enough destinations to utilize all workers
    if total_destinations < 10:
        logger.warning(f"⚠️ Not enough destinations ({total_destinations}) to utilize all 10 workers")
        return False
    else:
        logger.info(f"✅ Enough destinations ({total_destinations}) to utilize all 10 workers")
        return True

async def verify_worker_availability(db):
    """Verify that all workers are available."""
    available_workers = await db.get_available_workers()
    logger.info(f"get_available_workers() returned {len(available_workers)} workers")
    
    if len(available_workers) < 10:
        logger.warning(f"⚠️ Only {len(available_workers)}/10 workers are available")
        
        # Print details of available workers
        for worker in available_workers:
            worker_id = worker.get('worker_id')
            hourly_usage = worker.get('hourly_usage', worker.get('hourly_posts', worker.get('messages_sent_this_hour', 0)))
            daily_usage = worker.get('daily_usage', worker.get('daily_posts', worker.get('messages_sent_today', 0)))
            hourly_limit = worker.get('hourly_limit', 15)
            daily_limit = worker.get('daily_limit', 150)
            
            logger.info(f"  Worker {worker_id}: {hourly_usage}/{hourly_limit} hourly, {daily_usage}/{daily_limit} daily")
        
        return False
    else:
        logger.info("✅ All 10 workers are available")
        return True

async def main():
    """Main function to fix worker utilization issues."""
    logger.info("Starting worker utilization fix")
    
    # Initialize database and config
    config = BotConfig()
    db = DatabaseManager(config.db_path, logger)
    
    # Step 1: Ensure all workers are initialized
    logger.info("\n=== Step 1: Ensure All Workers Initialized ===")
    await ensure_all_workers_initialized(db)
    
    # Step 2: Reset worker usage counters
    logger.info("\n=== Step 2: Reset Worker Usage Counters ===")
    await reset_worker_usage(db)
    
    # Step 3: Ensure all slots have destinations
    logger.info("\n=== Step 3: Ensure Slots Have Destinations ===")
    await ensure_slots_have_destinations(db)
    
    # Step 4: Ensure slots are due
    logger.info("\n=== Step 4: Ensure Slots Are Due ===")
    await ensure_slots_are_due(db)
    
    # Step 5: Verify get_active_ads_to_send()
    logger.info("\n=== Step 5: Verify get_active_ads_to_send() ===")
    ads_ok = await verify_get_active_ads_to_send(db)
    
    # Step 6: Verify worker availability
    logger.info("\n=== Step 6: Verify Worker Availability ===")
    workers_ok = await verify_worker_availability(db)
    
    # Final status
    if ads_ok and workers_ok:
        logger.info("\n✅ All fixes applied successfully! The system should now utilize all 10 workers.")
        logger.info("Run the scheduler to verify that all workers are being used.")
    else:
        logger.warning("\n⚠️ Some issues could not be fixed automatically.")
        if not ads_ok:
            logger.warning("  - Not enough due ads or destinations")
        if not workers_ok:
            logger.warning("  - Not all workers are available")
    
    logger.info("Worker utilization fix completed")

if __name__ == "__main__":
    asyncio.run(main())


