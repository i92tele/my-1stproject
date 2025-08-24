#!/usr/bin/env python3
"""
Fix Workers System
Properly initializes all 10 workers and fixes the worker system
"""

import sqlite3
import logging
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_workers_system():
    """Fix the workers system by properly initializing all 10 workers."""
    try:
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        
        logger.info("🔧 Fixing Workers System...")
        
        # Clear existing worker data to start fresh
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Clear worker_usage table
        cursor.execute("DELETE FROM worker_usage")
        logger.info("Cleared existing worker_usage data")
        
        # Clear worker_cooldowns table
        cursor.execute("DELETE FROM worker_cooldowns")
        logger.info("Cleared existing worker_cooldowns data")
        
        # Get current time plus 1 minute for cooldown
        now = datetime.now()
        cooldown_time = (now + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Initialize 10 workers properly with correct column names
        for worker_id in range(1, 11):
            # Add to worker_usage with correct column names
            cursor.execute('''
                INSERT INTO worker_usage (
                    worker_id, hour, hourly_posts, daily_posts, day, 
                    messages_sent_today, messages_sent_this_hour, 
                    last_reset_date, last_reset_hour, updated_at, 
                    date, created_at, daily_limit, hourly_limit, 
                    is_active, last_used_at
                )
                VALUES (?, 0, 0, 0, ?, 0, 0, ?, 0, ?, ?, ?, 100, 10, 1, NULL)
            ''', (worker_id, now.strftime('%Y-%m-%d'), 
                  now.strftime('%Y-%m-%d'), 
                  now.strftime('%Y-%m-%d %H:%M:%S'),
                  now.strftime('%Y-%m-%d'),
                  now.strftime('%Y-%m-%d %H:%M:%S')))
            
            # Add to worker_cooldowns with a valid cooldown_until value
            cursor.execute('''
                INSERT INTO worker_cooldowns (worker_id, cooldown_until, created_at, is_active, last_used_at)
                VALUES (?, ?, ?, 1, NULL)
            ''', (worker_id, cooldown_time, now.strftime('%Y-%m-%d %H:%M:%S')))
            
            logger.info(f"Initialized worker {worker_id}")
        
        conn.commit()
        conn.close()
        
        # Verify workers are properly initialized
        workers = await db.get_available_workers()
        logger.info(f"✅ Successfully initialized {len(workers)} workers")
        
        for worker in workers:
            logger.info(f"  Worker {worker['worker_id']}: {worker.get('hourly_posts', 0)}/10 posts")
        
        logger.info("✅ Workers system fixed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing workers system: {e}")
        return False

def fix_workers_schema():
    """Fix the worker tables schema if needed."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check and fix worker_usage table
        cursor.execute("PRAGMA table_info(worker_usage)")
        usage_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"worker_usage columns: {usage_columns}")
        
        # Add missing columns to worker_usage
        if 'is_active' not in usage_columns:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN is_active BOOLEAN DEFAULT 1")
            logger.info("Added is_active column to worker_usage")
        
        if 'last_used_at' not in usage_columns:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN last_used_at TIMESTAMP")
            logger.info("Added last_used_at column to worker_usage")
        
        # Check and fix worker_cooldowns table
        cursor.execute("PRAGMA table_info(worker_cooldowns)")
        cooldown_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"worker_cooldowns columns: {cooldown_columns}")
        
        # Add missing columns to worker_cooldowns
        if 'is_active' not in cooldown_columns:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN is_active BOOLEAN DEFAULT 1")
            logger.info("Added is_active column to worker_cooldowns")
        
        if 'last_used_at' not in cooldown_columns:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN last_used_at TIMESTAMP")
            logger.info("Added last_used_at column to worker_cooldowns")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Worker tables schema fixed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker schema: {e}")
        return False

async def main():
    """Main function to fix both payments and workers."""
    logger.info("🚀 Starting Critical System Fixes...")
    
    # Fix payments schema
    logger.info("=" * 50)
    logger.info("🔧 FIXING PAYMENTS SYSTEM")
    logger.info("=" * 50)
    
    import fix_payments_schema
    payments_fixed = fix_payments_schema.fix_payments_schema()
    
    # Fix workers schema
    logger.info("=" * 50)
    logger.info("🔧 FIXING WORKERS SYSTEM")
    logger.info("=" * 50)
    
    workers_schema_fixed = fix_workers_schema()
    workers_fixed = await fix_workers_system()
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 FIX SUMMARY")
    logger.info("=" * 50)
    
    if payments_fixed:
        logger.info("✅ Payments system: FIXED")
    else:
        logger.error("❌ Payments system: FAILED")
    
    if workers_schema_fixed and workers_fixed:
        logger.info("✅ Workers system: FIXED")
    else:
        logger.error("❌ Workers system: FAILED")
    
    if payments_fixed and workers_schema_fixed and workers_fixed:
        logger.info("🎉 ALL CRITICAL ISSUES FIXED!")
        logger.info("🚀 Bot is now fully functional!")
    else:
        logger.error("❌ Some critical issues remain unfixed")

if __name__ == "__main__":
    asyncio.run(main())
