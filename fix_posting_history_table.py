#!/usr/bin/env python3
"""
Fix posting_history table by adding missing columns
"""

import sqlite3
import os

def fix_posting_history_table():
    """Fix the posting_history table structure."""
    print("🔧 Fixing posting_history table...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current table structure
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current posting_history columns: {column_names}")
        
        # Check for missing columns
        missing_columns = []
        
        if 'ban_detected' not in column_names:
            missing_columns.append('ban_detected')
        
        if 'ban_type' not in column_names:
            missing_columns.append('ban_type')
        
        if 'error_message' not in column_names:
            missing_columns.append('error_message')
        
        if 'message_content_hash' not in column_names:
            missing_columns.append('message_content_hash')
        
        # Add missing columns
        for column in missing_columns:
            if column == 'ban_detected':
                cursor.execute("ALTER TABLE posting_history ADD COLUMN ban_detected BOOLEAN DEFAULT 0")
                print(f"✅ Added ban_detected column")
            elif column == 'ban_type':
                cursor.execute("ALTER TABLE posting_history ADD COLUMN ban_type TEXT")
                print(f"✅ Added ban_type column")
            elif column == 'error_message':
                cursor.execute("ALTER TABLE posting_history ADD COLUMN error_message TEXT")
                print(f"✅ Added error_message column")
            elif column == 'message_content_hash':
                cursor.execute("ALTER TABLE posting_history ADD COLUMN message_content_hash TEXT")
                print(f"✅ Added message_content_hash column")
        
        conn.commit()
        
        # Verify the fix
        cursor.execute("PRAGMA table_info(posting_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Updated posting_history columns: {column_names}")
        
        # Check if all required columns exist
        required_columns = ['id', 'slot_id', 'worker_id', 'destination_id', 'posted_at', 'success', 'ban_detected', 'ban_type', 'error_message', 'message_content_hash']
        missing_required = [col for col in required_columns if col not in column_names]
        
        if missing_required:
            print(f"❌ Still missing required columns: {missing_required}")
            return False
        else:
            print("✅ All required columns present in posting_history table")
            return True
        
    except Exception as e:
        print(f"❌ Error fixing posting_history table: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run the fix."""
    print("🔧 Fixing Posting History Table")
    print("=" * 50)
    
    success = fix_posting_history_table()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 posting_history table fixed successfully!")
        print("✅ All required columns added")
        print("🚀 Bot should now work without 'ban_detected' errors")
    else:
        print("❌ Failed to fix posting_history table")

if __name__ == "__main__":
    main()
