#!/usr/bin/env python3
"""
Simple Worker Usage Fix

This script specifically fixes the created_at column issue in worker_usage table
"""

import sqlite3
import sys

def fix_worker_usage():
    """Fix the worker_usage table created_at column."""
    try:
        print("🔧 Fixing worker_usage table...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_usage);")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"📋 Current columns: {', '.join(columns)}")
        
        # Add missing columns
        missing_columns = [
            ('messages_sent_today', 'INTEGER DEFAULT 0'),
            ('messages_sent_this_hour', 'INTEGER DEFAULT 0'),
            ('last_reset_date', 'TEXT'),
            ('last_reset_hour', 'INTEGER'),
            ('created_at', 'TEXT'),  # Remove DEFAULT CURRENT_TIMESTAMP for ALTER TABLE
            ('updated_at', 'TEXT'),
            ('date', 'TEXT')
        ]
        
        added_count = 0
        for col_name, col_type in missing_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added: {col_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"ℹ️ {col_name} already exists")
                    else:
                        print(f"❌ Error adding {col_name}: {e}")
            else:
                print(f"ℹ️ {col_name} already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(worker_usage);")
        final_columns = [row[1] for row in cursor.fetchall()]
        
        print(f"\n📋 Final columns: {', '.join(final_columns)}")
        
        if 'created_at' in final_columns:
            print("✅ created_at column successfully added!")
            return True
        else:
            print("❌ created_at column still missing!")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing worker_usage: {e}")
        return False
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    print("=" * 50)
    print("WORKER USAGE TABLE FIX")
    print("=" * 50)
    
    success = fix_worker_usage()
    
    if success:
        print("\n🎉 WORKER USAGE TABLE FIXED!")
        print("The created_at column has been added successfully.")
    else:
        print("\n❌ WORKER USAGE TABLE FIX FAILED!")
        print("Please check the error messages above.")
    
    sys.exit(0 if success else 1)
