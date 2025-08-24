#!/usr/bin/env python3
"""
Clean Invalid Destinations

This script cleans up invalid destinations that are causing posting failures.
"""

import sqlite3
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def analyze_destinations():
    """Analyze destinations and identify invalid ones."""
    logger.info("🔍 Analyzing destinations...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Get all destinations
        cursor.execute('''
            SELECT destination_id, destination_name, slot_id, slot_type
            FROM slot_destinations
            ORDER BY slot_id, destination_id
        ''')
        
        destinations = cursor.fetchall()
        logger.info(f"Total destinations: {len(destinations)}")
        
        invalid_destinations = []
        valid_destinations = []
        
        for dest_id, dest_name, slot_id, slot_type in destinations:
            # Check for invalid patterns
            is_invalid = False
            reason = ""
            
            # Pattern 1: Destinations with invalid characters
            if re.search(r'[<>"\']', dest_id):
                is_invalid = True
                reason = "Invalid characters"
            
            # Pattern 2: Destinations that are too short
            elif len(dest_id) < 3:
                is_invalid = True
                reason = "Too short"
            
            # Pattern 3: Destinations with multiple slashes (forum topics should have only one)
            elif dest_id.count('/') > 1:
                is_invalid = True
                reason = "Multiple slashes"
            
            # Pattern 4: Destinations that don't start with @ or t.me/
            elif not (dest_id.startswith('@') or dest_id.startswith('t.me/')):
                is_invalid = True
                reason = "Invalid format"
            
            # Pattern 5: Forum topics with invalid topic IDs
            elif '/' in dest_id:
                parts = dest_id.split('/')
                if len(parts) == 2:
                    group_part = parts[0]
                    topic_part = parts[1]
                    
                    # Check if topic ID is numeric
                    if not topic_part.isdigit():
                        is_invalid = True
                        reason = "Invalid topic ID"
                    
                    # Check if group part is valid
                    if not (group_part.startswith('@') or group_part.startswith('t.me/')):
                        is_invalid = True
                        reason = "Invalid group format"
            
            if is_invalid:
                invalid_destinations.append({
                    'destination_id': dest_id,
                    'destination_name': dest_name,
                    'slot_id': slot_id,
                    'slot_type': slot_type,
                    'reason': reason
                })
            else:
                valid_destinations.append({
                    'destination_id': dest_id,
                    'destination_name': dest_name,
                    'slot_id': slot_id,
                    'slot_type': slot_type
                })
        
        logger.info(f"Valid destinations: {len(valid_destinations)}")
        logger.info(f"Invalid destinations: {len(invalid_destinations)}")
        
        if invalid_destinations:
            logger.warning("Invalid destinations found:")
            for dest in invalid_destinations[:10]:  # Show first 10
                logger.warning(f"  {dest['destination_id']} (Slot {dest['slot_id']}) - {dest['reason']}")
            
            if len(invalid_destinations) > 10:
                logger.warning(f"  ... and {len(invalid_destinations) - 10} more")
        
        return invalid_destinations, valid_destinations
        
    except Exception as e:
        logger.error(f"❌ Error analyzing destinations: {e}")
        return [], []
    finally:
        conn.close()

def clean_invalid_destinations(invalid_destinations):
    """Remove invalid destinations from the database."""
    logger.info("🧹 Cleaning invalid destinations...")
    
    if not invalid_destinations:
        logger.info("✅ No invalid destinations to clean")
        return True
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        cleaned_count = 0
        
        for dest in invalid_destinations:
            try:
                cursor.execute('''
                    DELETE FROM slot_destinations 
                    WHERE destination_id = ? AND slot_id = ? AND slot_type = ?
                ''', (dest['destination_id'], dest['slot_id'], dest['slot_type']))
                
                if cursor.rowcount > 0:
                    cleaned_count += 1
                    logger.info(f"  Cleaned: {dest['destination_id']} (Slot {dest['slot_id']}) - {dest['reason']}")
                
            except Exception as e:
                logger.error(f"  Error cleaning {dest['destination_id']}: {e}")
        
        conn.commit()
        logger.info(f"✅ Cleaned {cleaned_count} invalid destinations")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cleaning destinations: {e}")
        return False
    finally:
        conn.close()

def verify_cleaning():
    """Verify that cleaning was successful."""
    logger.info("🔍 Verifying cleaning results...")
    
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Count remaining destinations
        cursor.execute('SELECT COUNT(*) FROM slot_destinations')
        total_destinations = cursor.fetchone()[0]
        
        # Count destinations by slot
        cursor.execute('''
            SELECT slot_id, COUNT(*) as count 
            FROM slot_destinations 
            GROUP BY slot_id 
            ORDER BY slot_id
        ''')
        
        slot_counts = cursor.fetchall()
        
        logger.info(f"Total destinations remaining: {total_destinations}")
        logger.info("Destinations by slot:")
        for slot_id, count in slot_counts:
            logger.info(f"  Slot {slot_id}: {count} destinations")
        
        return total_destinations
        
    except Exception as e:
        logger.error(f"❌ Error verifying cleaning: {e}")
        return 0
    finally:
        conn.close()

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🧹 CLEAN INVALID DESTINATIONS")
    logger.info("=" * 60)
    
    # Step 1: Analyze destinations
    invalid_destinations, valid_destinations = analyze_destinations()
    
    if not invalid_destinations:
        logger.info("✅ No invalid destinations found")
        return
    
    # Step 2: Clean invalid destinations
    if clean_invalid_destinations(invalid_destinations):
        logger.info("✅ Cleaning completed successfully")
    else:
        logger.error("❌ Cleaning failed")
        return
    
    # Step 3: Verify cleaning
    final_count = verify_cleaning()
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Invalid destinations removed: {len(invalid_destinations)}")
    logger.info(f"Valid destinations remaining: {len(valid_destinations)}")
    logger.info(f"Total destinations after cleaning: {final_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
