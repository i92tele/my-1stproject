#!/usr/bin/env python3
"""
Cleanup Destinations

This script identifies and optionally disables problematic destinations
that have a high failure rate.

Usage:
    python cleanup_destinations.py [--disable]

Options:
    --disable    Actually disable problematic destinations in the database
"""

import os
import sys
import sqlite3
import logging
import argparse
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

def cleanup_destinations(disable=False):
    """Identify and optionally disable problematic destinations."""
    logger.info("🔍 Analyzing destination performance...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if destinations table has is_active column
        cursor.execute("PRAGMA table_info(destinations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        has_active_column = "is_active" in columns
        if not has_active_column and disable:
            logger.info("Adding is_active column to destinations table...")
            cursor.execute("ALTER TABLE destinations ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.commit()
        
        # Get destinations with high failure rates
        query = """
        SELECT d.destination_id, d.name, 
               COUNT(CASE WHEN ph.success = 0 THEN 1 END) as failures,
               COUNT(*) as total_attempts,
               (COUNT(CASE WHEN ph.success = 0 THEN 1 END) * 100.0 / COUNT(*)) as failure_rate
        FROM destinations d
        LEFT JOIN posting_history ph ON d.destination_id = ph.destination_id
        GROUP BY d.destination_id
        HAVING failures > 5 AND (failures * 1.0 / total_attempts) > 0.8
        ORDER BY failure_rate DESC, total_attempts DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            logger.info("✅ No problematic destinations found")
            return
        
        # Display problematic destinations
        logger.info(f"Found {len(results)} problematic destinations:")
        print("\n{:<40} {:<10} {:<10} {:<10}".format("Destination", "Failures", "Total", "Rate %"))
        print("-" * 70)
        
        for row in results:
            print("{:<40} {:<10} {:<10} {:<10.1f}".format(
                f"{row['name']} ({row['destination_id']})",
                row['failures'],
                row['total_attempts'],
                row['failure_rate']
            ))
        
        # Disable problematic destinations if requested
        if disable and has_active_column:
            destination_ids = [row['destination_id'] for row in results]
            placeholders = ', '.join(['?' for _ in destination_ids])
            
            cursor.execute(f"UPDATE destinations SET is_active = 0 WHERE destination_id IN ({placeholders})", destination_ids)
            conn.commit()
            
            logger.info(f"✅ Disabled {len(destination_ids)} problematic destinations")
        elif disable:
            logger.warning("⚠️ Could not disable destinations: is_active column not found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up destinations: {e}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Cleanup problematic destinations")
    parser.add_argument("--disable", action="store_true", help="Disable problematic destinations")
    args = parser.parse_args()
    
    cleanup_destinations(args.disable)

if __name__ == "__main__":
    main()
