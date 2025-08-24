#!/usr/bin/env python3
"""
Trigger Posting Process

This script manually triggers the posting process for all due ads.
It's useful for testing if the posting functionality works correctly.

Usage:
    python trigger_posting.py [--force]

Options:
    --force    Force posting of all ads regardless of schedule
"""

import sqlite3
import logging
import argparse
import sys
import os
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

async def trigger_posting(force=False):
    """Trigger posting process for all due ads."""
    logger.info("🚀 Triggering posting process...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if ad_slots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ad_slots'")
        if cursor.fetchone() is None:
            logger.error("❌ ad_slots table does not exist")
            conn.close()
            return False
        
        # Get due ad slots
        if force:
            # Get all non-paused ad slots
            cursor.execute("""
                SELECT 
                    a.id, 
                    a.user_id, 
                    a.slot_type, 
                    a.content,
                    a.frequency_hours, 
                    a.last_sent_at,
                    COUNT(d.id) as destination_count
                FROM 
                    ad_slots a
                LEFT JOIN 
                    destinations d ON a.id = d.slot_id
                WHERE 
                    (a.is_paused = 0 OR a.is_paused IS NULL)
                GROUP BY 
                    a.id
                ORDER BY 
                    a.last_sent_at ASC
            """)
        else:
            # Get only due ad slots
            cursor.execute("""
                SELECT 
                    a.id, 
                    a.user_id, 
                    a.slot_type, 
                    a.content,
                    a.frequency_hours, 
                    a.last_sent_at,
                    COUNT(d.id) as destination_count
                FROM 
                    ad_slots a
                LEFT JOIN 
                    destinations d ON a.id = d.slot_id
                WHERE 
                    (a.is_paused = 0 OR a.is_paused IS NULL) AND
                    (
                        a.last_sent_at IS NULL OR 
                        datetime(a.last_sent_at, '+' || a.frequency_hours || ' hours') <= datetime('now')
                    )
                GROUP BY 
                    a.id
                ORDER BY 
                    a.last_sent_at ASC
            """)
        
        results = cursor.fetchall()
        
        if not results:
            logger.info("No ad slots due for posting")
            conn.close()
            return True
        
        logger.info(f"Found {len(results)} ad slots to post")
        
        # Import necessary modules
        sys.path.insert(0, os.path.abspath("."))
        
        try:
            # Try to import from scheduler module first
            from scheduler.core.posting_service import PostingService
            from src.database.manager import DatabaseManager
            logger.info("✅ Successfully imported from scheduler module")
            using_new_structure = True
        except ImportError:
            try:
                # Fall back to direct imports
                from posting_service import PostingService
                from database import DatabaseManager
                logger.info("✅ Successfully imported from root directory")
                using_new_structure = False
            except ImportError:
                logger.error("❌ Could not import required modules")
                conn.close()
                return False
        
        # Initialize database manager
        try:
            db_manager = DatabaseManager(DATABASE_PATH, logger)
            logger.info("✅ Database manager initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing database manager: {e}")
            conn.close()
            return False
        
        # Initialize worker clients
        try:
            if using_new_structure:
                from scheduler.workers.worker_client import WorkerClient
                from scheduler.config.worker_config import WorkerConfig
            else:
                from worker_client import WorkerClient
                from worker_config import WorkerConfig
                
            worker_config = WorkerConfig()
            worker_credentials = worker_config.get_all_worker_credentials()
            
            workers = []
            for creds in worker_credentials:
                worker = WorkerClient(
                    api_id=creds['api_id'],
                    api_hash=creds['api_hash'],
                    phone=creds['phone'],
                    worker_id=creds['worker_id']
                )
                workers.append(worker)
                
            logger.info(f"✅ Initialized {len(workers)} worker clients")
        except Exception as e:
            logger.error(f"❌ Error initializing worker clients: {e}")
            conn.close()
            return False
        
        # Initialize posting service
        try:
            posting_service = PostingService(workers, db_manager)
            logger.info("✅ Posting service initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing posting service: {e}")
            conn.close()
            return False
        
        # Trigger posting for each ad slot
        for row in results:
            slot_id = row['id']
            slot_type = row['slot_type']
            destination_count = row['destination_count']
            
            logger.info(f"Processing slot {slot_id} ({slot_type}) with {destination_count} destinations...")
            
            # Get slot details
            cursor.execute("""
                SELECT * FROM ad_slots WHERE id = ?
            """, (slot_id,))
            slot = dict(cursor.fetchone())
            
            # Get destinations
            cursor.execute("""
                SELECT * FROM destinations WHERE slot_id = ?
            """, (slot_id,))
            destinations = [dict(row) for row in cursor.fetchall()]
            
            if not destinations:
                logger.warning(f"⚠️ Slot {slot_id} has no destinations, skipping")
                continue
            
            # Add destinations to slot
            slot['destinations'] = destinations
            
            # Trigger posting
            try:
                logger.info(f"Triggering posting for slot {slot_id}...")
                
                # Call post_ads with this slot
                result = await posting_service.post_ads([slot])
                
                logger.info(f"✅ Posting result for slot {slot_id}: {result}")
                
                # Update last_sent_at
                cursor.execute("""
                    UPDATE ad_slots SET last_sent_at = datetime('now') WHERE id = ?
                """, (slot_id,))
                conn.commit()
                
            except Exception as e:
                logger.error(f"❌ Error posting slot {slot_id}: {e}")
        
        conn.close()
        logger.info("✅ Posting process completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error triggering posting: {e}")
        return False

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Trigger posting process for all due ads")
    parser.add_argument("--force", action="store_true", help="Force posting of all ads regardless of schedule")
    args = parser.parse_args()
    
    await trigger_posting(args.force)

if __name__ == "__main__":
    asyncio.run(main())
