#!/usr/bin/env python3
"""
Fix Payments Table Schema
Adds missing columns to the payments table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_payments_schema():
    """Fix the payments table schema by adding missing columns."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(payments)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Current payments table columns: {columns}")
        
        # Add missing columns
        missing_columns = []
        
        if 'tier' not in columns:
            missing_columns.append("tier TEXT")
        if 'amount_usd' not in columns:
            missing_columns.append("amount_usd REAL")
        if 'amount_crypto' not in columns:
            missing_columns.append("amount_crypto REAL")
        if 'crypto_type' not in columns:
            missing_columns.append("crypto_type TEXT")
        if 'status' not in columns:
            missing_columns.append("status TEXT DEFAULT 'pending'")
        if 'created_at' not in columns:
            missing_columns.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        if missing_columns:
            logger.info(f"Adding missing columns: {missing_columns}")
            for column_def in missing_columns:
                try:
                    cursor.execute(f"ALTER TABLE payments ADD COLUMN {column_def}")
                    logger.info(f"Added column: {column_def}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        logger.info(f"Column already exists: {column_def}")
                    else:
                        logger.error(f"Error adding column {column_def}: {e}")
        else:
            logger.info("All required columns already exist")
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(payments)")
        final_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Final payments table columns: {final_columns}")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Payments table schema fixed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing payments schema: {e}")
        return False

if __name__ == "__main__":
    fix_payments_schema()
