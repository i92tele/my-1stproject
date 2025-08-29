#!/usr/bin/env python3
"""
Script to check why get_active_ads_to_send() might not be returning all due ads.
This helps diagnose why only 2 workers are being used despite 10 being available.
"""

import asyncio
import sys
import os
import logging
import sqlite3
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database.manager import DatabaseManager
from config import BotConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("due_ads_check")

async def check_ad_slots_table(db):
    """Check the ad_slots table structure and data."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(ad_slots)")
    columns = cursor.fetchall()
    logger.info(f"ad_slots table has {len(columns)} columns:")
    for col in columns:
        logger.info(f"  {col[1]} ({col[2]})")
    
    # Check total slots
    cursor.execute("SELECT COUNT(*) FROM ad_slots")
    total_slots = cursor.fetchone()[0]
    logger.info(f"Total user slots: {total_slots}")
    
    # Check active slots
    cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
    active_slots = cursor.fetchone()[0]
    logger.info(f"Active user slots: {active_slots}")
    
    # Check slots with content
    cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE content IS NOT NULL AND content != ''")
    slots_with_content = cursor.fetchone()[0]
    logger.info(f"User slots with content: {slots_with_content}")
    
    # Check slots that are due
    cursor.execute("""
        SELECT COUNT(*) FROM ad_slots 
        WHERE is_active = 1 
        AND content IS NOT NULL 
        AND content != ''
        AND (
            last_sent_at IS NULL 
            OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
        )
    """)
    due_slots = cursor.fetchone()[0]
    logger.info(f"Due user slots: {due_slots}")
    
    # List the due slots
    cursor.execute("""
        SELECT id, user_id, last_sent_at, interval_minutes, 
               CASE WHEN last_sent_at IS NULL THEN 'Never sent'
                    ELSE datetime(last_sent_at, '+' || interval_minutes || ' minutes')
               END as next_due
        FROM ad_slots 
        WHERE is_active = 1 
        AND content IS NOT NULL 
        AND content != ''
        AND (
            last_sent_at IS NULL 
            OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
        )
    """)
    due_slot_details = cursor.fetchall()
    if due_slot_details:
        logger.info("Due user slot details:")
        for slot in due_slot_details:
            logger.info(f"  Slot {slot[0]} (User {slot[1]}): Last sent at {slot[2]}, Next due at {slot[4]}")
    
    conn.close()

async def check_admin_slots_table(db):
    """Check the admin_ad_slots table structure and data."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    try:
        cursor.execute("PRAGMA table_info(admin_ad_slots)")
        columns = cursor.fetchall()
        if not columns:
            logger.info("admin_ad_slots table does not exist or is empty")
            conn.close()
            return
        
        logger.info(f"admin_ad_slots table has {len(columns)} columns:")
        for col in columns:
            logger.info(f"  {col[1]} ({col[2]})")
        
        # Check total slots
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
        total_slots = cursor.fetchone()[0]
        logger.info(f"Total admin slots: {total_slots}")
        
        # Check active slots
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
        active_slots = cursor.fetchone()[0]
        logger.info(f"Active admin slots: {active_slots}")
        
        # Check slots with content
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE content IS NOT NULL AND content != ''")
        slots_with_content = cursor.fetchone()[0]
        logger.info(f"Admin slots with content: {slots_with_content}")
        
        # Check slots that are due
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots 
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
            AND (
                last_sent_at IS NULL 
                OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
            )
        """)
        due_slots = cursor.fetchone()[0]
        logger.info(f"Due admin slots: {due_slots}")
        
        # List the due slots
        cursor.execute("""
            SELECT id, last_sent_at, interval_minutes, 
                   CASE WHEN last_sent_at IS NULL THEN 'Never sent'
                        ELSE datetime(last_sent_at, '+' || interval_minutes || ' minutes')
                   END as next_due
            FROM admin_ad_slots 
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
            AND (
                last_sent_at IS NULL 
                OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
            )
        """)
        due_slot_details = cursor.fetchall()
        if due_slot_details:
            logger.info("Due admin slot details:")
            for slot in due_slot_details:
                logger.info(f"  Slot {slot[0]}: Last sent at {slot[1]}, Next due at {slot[3]}")
    
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking admin_ad_slots: {e}")
    
    conn.close()

async def check_destinations(db):
    """Check the destinations for slots."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check user slot destinations
    cursor.execute("""
        SELECT s.id, COUNT(d.id) as destination_count
        FROM ad_slots s
        LEFT JOIN slot_destinations d ON s.id = d.slot_id AND d.is_active = 1
        WHERE s.is_active = 1 
        AND s.content IS NOT NULL 
        AND s.content != ''
        GROUP BY s.id
    """)
    slot_destinations = cursor.fetchall()
    logger.info("User slot destination counts:")
    for slot in slot_destinations:
        logger.info(f"  Slot {slot[0]}: {slot[1]} destinations")
    
    # Check if any active slots have zero destinations
    cursor.execute("""
        SELECT COUNT(*) FROM ad_slots s
        WHERE s.is_active = 1 
        AND s.content IS NOT NULL 
        AND s.content != ''
        AND NOT EXISTS (
            SELECT 1 FROM slot_destinations d 
            WHERE d.slot_id = s.id AND d.is_active = 1
        )
    """)
    slots_without_destinations = cursor.fetchone()[0]
    if slots_without_destinations > 0:
        logger.warning(f"⚠️ {slots_without_destinations} active user slots have no destinations!")
    
    # Check admin slot destinations if table exists
    try:
        cursor.execute("""
            SELECT s.id, COUNT(d.id) as destination_count
            FROM admin_ad_slots s
            LEFT JOIN admin_slot_destinations d ON s.id = d.slot_id AND d.is_active = 1
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            GROUP BY s.id
        """)
        admin_slot_destinations = cursor.fetchall()
        logger.info("Admin slot destination counts:")
        for slot in admin_slot_destinations:
            logger.info(f"  Slot {slot[0]}: {slot[1]} destinations")
        
        # Check if any active admin slots have zero destinations
        cursor.execute("""
            SELECT COUNT(*) FROM admin_ad_slots s
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            AND NOT EXISTS (
                SELECT 1 FROM admin_slot_destinations d 
                WHERE d.slot_id = s.id AND d.is_active = 1
            )
        """)
        admin_slots_without_destinations = cursor.fetchone()[0]
        if admin_slots_without_destinations > 0:
            logger.warning(f"⚠️ {admin_slots_without_destinations} active admin slots have no destinations!")
    
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking admin slot destinations: {e}")
    
    conn.close()

async def check_worker_limits(db):
    """Check worker limits and usage."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check worker_usage table
    try:
        cursor.execute("PRAGMA table_info(worker_usage)")
        columns = cursor.fetchall()
        if columns:
            logger.info(f"worker_usage table has {len(columns)} columns:")
            for col in columns:
                logger.info(f"  {col[1]} ({col[2]})")
            
            # Check worker usage
            cursor.execute("SELECT * FROM worker_usage")
            usage_data = cursor.fetchall()
            logger.info(f"Worker usage records: {len(usage_data)}")
            
            # Get column names
            column_names = [col[1] for col in columns]
            
            # Print worker usage data
            if usage_data:
                logger.info("Worker usage details:")
                for row in usage_data:
                    worker_info = {}
                    for i, value in enumerate(row):
                        if i < len(column_names):
                            worker_info[column_names[i]] = value
                    
                    worker_id = worker_info.get('worker_id', 'Unknown')
                    hourly_posts = worker_info.get('hourly_posts', worker_info.get('messages_sent_this_hour', 0))
                    daily_posts = worker_info.get('daily_posts', worker_info.get('messages_sent_today', 0))
                    hourly_limit = worker_info.get('hourly_limit', 15)
                    daily_limit = worker_info.get('daily_limit', 150)
                    
                    logger.info(f"  Worker {worker_id}: {hourly_posts}/{hourly_limit} hourly, {daily_posts}/{daily_limit} daily")
        else:
            logger.warning("worker_usage table does not exist or is empty")
    
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking worker_usage: {e}")
    
    # Check worker_cooldowns table
    try:
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        columns = cursor.fetchall()
        if columns:
            logger.info(f"worker_cooldowns table has {len(columns)} columns:")
            for col in columns:
                logger.info(f"  {col[1]} ({col[2]})")
            
            # Check active workers
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns WHERE is_active = 1")
            active_workers = cursor.fetchone()[0]
            logger.info(f"Active workers: {active_workers}")
            
            # Get worker details
            cursor.execute("SELECT worker_id, is_active, last_used_at FROM worker_cooldowns")
            workers = cursor.fetchall()
            if workers:
                logger.info("Worker details:")
                for worker in workers:
                    status = "Active" if worker[1] else "Inactive"
                    logger.info(f"  Worker {worker[0]}: {status}, Last used at {worker[2]}")
        else:
            logger.warning("worker_cooldowns table does not exist or is empty")
    
    except sqlite3.OperationalError as e:
        logger.warning(f"Error checking worker_cooldowns: {e}")
    
    conn.close()

async def check_active_ads_to_send(db):
    """Check what get_active_ads_to_send() returns."""
    try:
        # Get active ads
        active_ads = await db.get_active_ads_to_send()
        logger.info(f"get_active_ads_to_send() returned {len(active_ads)} slots")
        
        # Print details of each slot
        if active_ads:
            logger.info("Active ads details:")
            for ad in active_ads:
                slot_id = ad.get('id')
                slot_type = ad.get('slot_type', 'user')
                last_sent = ad.get('last_sent_at')
                interval = ad.get('interval_minutes')
                
                logger.info(f"  Slot {slot_id} ({slot_type}): Last sent at {last_sent}, Interval: {interval} minutes")
                
                # Get destinations for this slot
                destinations = await db.get_slot_destinations(slot_id, slot_type)
                logger.info(f"    Destinations: {len(destinations)}")
                
                # Print first few destinations
                for i, dest in enumerate(destinations[:3]):
                    logger.info(f"      {i+1}. {dest.get('destination_name', 'Unknown')} ({dest.get('destination_id', 'Unknown')})")
                
                if len(destinations) > 3:
                    logger.info(f"      ... and {len(destinations) - 3} more")
        else:
            logger.warning("⚠️ No active ads to send!")
    
    except Exception as e:
        logger.error(f"Error checking active ads: {e}")

async def check_users_table(db):
    """Check the users table for subscription issues."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check table structure
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    logger.info(f"users table has {len(columns)} columns:")
    for col in columns:
        logger.info(f"  {col[1]} ({col[2]})")
    
    # Check total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    logger.info(f"Total users: {total_users}")
    
    # Check users with active subscriptions
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE subscription_expires IS NOT NULL 
        AND datetime('now') < datetime(subscription_expires)
    """)
    active_subscriptions = cursor.fetchone()[0]
    logger.info(f"Users with active subscriptions: {active_subscriptions}")
    
    # Get user details
    cursor.execute("""
        SELECT user_id, username, subscription_tier, subscription_expires,
               CASE WHEN subscription_expires IS NULL THEN 'No subscription'
                    WHEN datetime('now') < datetime(subscription_expires) THEN 'Active'
                    ELSE 'Expired'
               END as status
        FROM users
    """)
    users = cursor.fetchall()
    if users:
        logger.info("User details:")
        for user in users:
            logger.info(f"  User {user[0]} ({user[1]}): {user[2]}, Expires: {user[3]}, Status: {user[4]}")
    
    conn.close()

async def check_database_health(db):
    """Check overall database health."""
    try:
        # Check if database file exists
        if not os.path.exists(db.db_path):
            logger.error(f"Database file does not exist: {db.db_path}")
            return
        
        # Check file size
        file_size = os.path.getsize(db.db_path)
        logger.info(f"Database file size: {file_size / 1024:.2f} KB")
        
        # Try to open the database
        conn = sqlite3.connect(db.db_path)
        
        # Check for corruption
        try:
            conn.execute("PRAGMA integrity_check")
            logger.info("Database integrity check passed")
        except sqlite3.DatabaseError as e:
            logger.error(f"Database integrity check failed: {e}")
        
        # Check for foreign key constraints
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        foreign_keys = cursor.fetchone()[0]
        logger.info(f"Foreign key constraints: {'Enabled' if foreign_keys else 'Disabled'}")
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Database has {len(tables)} tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            logger.info(f"  {table[0]}: {count} rows")
        
        conn.close()
    
    except Exception as e:
        logger.error(f"Error checking database health: {e}")

async def check_timestamp_issues(db):
    """Check for timestamp format issues that might affect due calculation."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Check user slots with last_sent_at
    cursor.execute("""
        SELECT id, last_sent_at, interval_minutes,
               datetime('now') as current_time,
               datetime(last_sent_at, '+' || interval_minutes || ' minutes') as next_due,
               CASE WHEN datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
                    THEN 'Due'
                    ELSE 'Not Due'
               END as status
        FROM ad_slots
        WHERE last_sent_at IS NOT NULL
        LIMIT 10
    """)
    slots = cursor.fetchall()
    if slots:
        logger.info("Timestamp calculations for user slots:")
        for slot in slots:
            logger.info(f"  Slot {slot[0]}: Last sent at {slot[1]}, Interval: {slot[2]} minutes")
            logger.info(f"    Current time: {slot[3]}")
            logger.info(f"    Next due: {slot[4]}")
            logger.info(f"    Status: {slot[5]}")
    
    # Check admin slots with last_sent_at
    try:
        cursor.execute("""
            SELECT id, last_sent_at, interval_minutes,
                   datetime('now') as current_time,
                   datetime(last_sent_at, '+' || interval_minutes || ' minutes') as next_due,
                   CASE WHEN datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
                        THEN 'Due'
                        ELSE 'Not Due'
                   END as status
            FROM admin_ad_slots
            WHERE last_sent_at IS NOT NULL
            LIMIT 10
        """)
        admin_slots = cursor.fetchall()
        if admin_slots:
            logger.info("Timestamp calculations for admin slots:")
            for slot in admin_slots:
                logger.info(f"  Slot {slot[0]}: Last sent at {slot[1]}, Interval: {slot[2]} minutes")
                logger.info(f"    Current time: {slot[3]}")
                logger.info(f"    Next due: {slot[4]}")
                logger.info(f"    Status: {slot[5]}")
    except sqlite3.OperationalError:
        pass
    
    conn.close()

async def force_due_ads(db):
    """Force some ads to be due by updating their last_sent_at timestamp."""
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # Get current time
    now = datetime.now()
    
    # Set some user slots to be due
    cursor.execute("""
        UPDATE ad_slots
        SET last_sent_at = ?
        WHERE is_active = 1
        AND content IS NOT NULL
        AND content != ''
        LIMIT 3
    """, ((now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),))
    
    user_slots_updated = cursor.rowcount
    logger.info(f"Updated {user_slots_updated} user slots to be due")
    
    # Set some admin slots to be due if table exists
    try:
        cursor.execute("""
            UPDATE admin_ad_slots
            SET last_sent_at = ?
            WHERE is_active = 1
            AND content IS NOT NULL
            AND content != ''
            LIMIT 2
        """, ((now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),))
        
        admin_slots_updated = cursor.rowcount
        logger.info(f"Updated {admin_slots_updated} admin slots to be due")
    except sqlite3.OperationalError:
        logger.info("Skipped updating admin slots (table may not exist)")
    
    conn.commit()
    conn.close()

async def main():
    """Main function to check why get_active_ads_to_send() might not be returning all due ads."""
    logger.info("Starting due ads check")
    
    # Initialize database and config
    config = BotConfig()
    db = DatabaseManager(config.db_path, logger)
    
    # Check database health
    logger.info("\n=== Database Health ===")
    await check_database_health(db)
    
    # Check users table
    logger.info("\n=== Users Table ===")
    await check_users_table(db)
    
    # Check ad_slots table
    logger.info("\n=== Ad Slots Table ===")
    await check_ad_slots_table(db)
    
    # Check admin_ad_slots table
    logger.info("\n=== Admin Ad Slots Table ===")
    await check_admin_slots_table(db)
    
    # Check destinations
    logger.info("\n=== Destinations ===")
    await check_destinations(db)
    
    # Check worker limits
    logger.info("\n=== Worker Limits ===")
    await check_worker_limits(db)
    
    # Check timestamp issues
    logger.info("\n=== Timestamp Calculations ===")
    await check_timestamp_issues(db)
    
    # Check what get_active_ads_to_send() returns
    logger.info("\n=== Active Ads to Send ===")
    await check_active_ads_to_send(db)
    
    # Optionally force some ads to be due
    logger.info("\n=== Forcing Ads to be Due ===")
    await force_due_ads(db)
    
    # Check again after forcing ads to be due
    logger.info("\n=== Active Ads to Send (After Force) ===")
    await check_active_ads_to_send(db)
    
    logger.info("Due ads check completed")

if __name__ == "__main__":
    asyncio.run(main())


