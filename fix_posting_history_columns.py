#!/usr/bin/env python3
"""
Fix Posting History Columns

Add missing columns to posting_history table to prevent recovery errors.
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

def fix_posting_history_columns():
    """Add missing columns to posting_history table."""
    logger.info("🔧 Fixing posting_history table columns...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check if posting_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history'")
        if not cursor.fetchone():
            logger.error("❌ posting_history table does not exist")
            return False
        
        # Get current columns
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Current columns: {columns}")
        
        # Add missing columns
        missing_columns = [
            ("ban_detected", "INTEGER DEFAULT 0"),
            ("ban_type", "TEXT"),
            ("error_message", "TEXT"),
            ("message_content_hash", "TEXT")
        ]
        
        added_columns = []
        for col_name, col_type in missing_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE posting_history ADD COLUMN {col_name} {col_type}")
                    added_columns.append(col_name)
                    logger.info(f"✅ Added column: {col_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not add column {col_name}: {e}")
        
        conn.commit()
        conn.close()
        
        if added_columns:
            logger.info(f"✅ Added {len(added_columns)} columns: {added_columns}")
        else:
            logger.info("✅ All columns already exist")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing posting_history columns: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🔧 FIXING POSTING HISTORY COLUMNS")
    logger.info("=" * 60)
    
    success = fix_posting_history_columns()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ Posting history columns fixed successfully!")
        logger.info("The restart recovery error should be resolved.")
    else:
        logger.error("❌ Failed to fix posting history columns")
    logger.info("=" * 60)
