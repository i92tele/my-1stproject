#!/usr/bin/env python3
"""
Fix database schema by adding missing last_checked column to payments table.
"""

import sqlite3
import os
from datetime import datetime

def fix_database_schema():
    """Add missing last_checked column to payments table."""
    
    # Database path
    db_path = "bot_database.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if last_checked column exists
        cursor.execute("PRAGMA table_info(payments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_checked' not in columns:
            print("🔧 Adding last_checked column to payments table...")
            cursor.execute('ALTER TABLE payments ADD COLUMN last_checked TEXT')
            conn.commit()
            print("✅ last_checked column added successfully!")
        else:
            print("✅ last_checked column already exists")
        
        # Update existing payments to have last_checked value
        cursor.execute("UPDATE payments SET last_checked = updated_at WHERE last_checked IS NULL")
        updated_count = cursor.rowcount
        if updated_count > 0:
            print(f"✅ Updated {updated_count} existing payments with last_checked timestamp")
        
        conn.commit()
        conn.close()
        
        print("🎉 Database schema fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing database schema...")
    success = fix_database_schema()
    if success:
        print("✅ Ready to test payments!")
    else:
        print("❌ Database fix failed!")
