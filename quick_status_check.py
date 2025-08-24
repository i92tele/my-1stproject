#!/usr/bin/env python3
"""
Quick Status Check for AutoFarming Bot

This script provides a quick overview of the current system status.
"""

import sqlite3
import os
from datetime import datetime

def quick_status_check():
    """Perform a quick status check of the system."""
    print("🔍 QUICK STATUS CHECK")
    print("=" * 50)
    
    db_path = 'bot_database.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print(f"✅ Database file exists: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Tables found: {len(tables)}")
        for table in sorted(tables):
            print(f"  • {table}")
        
        # Check worker_usage
        if 'worker_usage' in tables:
            cursor.execute("SELECT COUNT(*) FROM worker_usage")
            worker_count = cursor.fetchone()[0]
            print(f"\n👥 Worker Usage: {worker_count} records")
            
            if worker_count > 0:
                cursor.execute("SELECT worker_id FROM worker_usage ORDER BY worker_id")
                worker_ids = [row[0] for row in cursor.fetchall()]
                print(f"  Worker IDs: {worker_ids}")
                
                # Check for duplicates
                cursor.execute("SELECT worker_id, COUNT(*) FROM worker_usage GROUP BY worker_id HAVING COUNT(*) > 1")
                duplicates = cursor.fetchall()
                if duplicates:
                    print(f"  ⚠️ Duplicates found: {len(duplicates)}")
                else:
                    print("  ✅ No duplicates")
        
        # Check worker_cooldowns
        if 'worker_cooldowns' in tables:
            cursor.execute("SELECT COUNT(*) FROM worker_cooldowns")
            cooldown_count = cursor.fetchone()[0]
            print(f"\n⏰ Worker Cooldowns: {cooldown_count} records")
        
        # Check ad_slots
        if 'ad_slots' in tables:
            cursor.execute("SELECT COUNT(*) FROM ad_slots")
            slot_count = cursor.fetchone()[0]
            print(f"\n📢 Ad Slots: {slot_count} records")
            
            if slot_count > 0:
                cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE last_sent_at IS NULL")
                null_timestamps = cursor.fetchone()[0]
                print(f"  Slots with NULL timestamps: {null_timestamps}")
        
        # Check posting_history
        if 'posting_history' in tables:
            cursor.execute("SELECT COUNT(*) FROM posting_history")
            history_count = cursor.fetchone()[0]
            print(f"\n📜 Posting History: {history_count} records")
        
        print(f"\n✅ Status check completed at {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during status check: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    quick_status_check()

