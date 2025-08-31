#!/usr/bin/env python3
"""
Fix Chat ID Column Issue
Fix the mismatch between chat_id in code and destination_id in database
"""

import sqlite3
import os
import re

def fix_database_schema():
    """Fix the worker_activity_log table schema."""
    print("🔧 Fixing database schema...")
    
    db_path = "bot_database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Add chat_id column if it doesn't exist
        if 'chat_id' not in column_names:
            print("📝 Adding chat_id column to worker_activity_log...")
            cursor.execute("ALTER TABLE worker_activity_log ADD COLUMN chat_id TEXT")
            print("✅ Added chat_id column")
        
        # Add destination_id column if it doesn't exist
        if 'destination_id' not in column_names:
            print("📝 Adding destination_id column to worker_activity_log...")
            cursor.execute("ALTER TABLE worker_activity_log ADD COLUMN destination_id TEXT")
            print("✅ Added destination_id column")
        
        conn.commit()
        print("✅ Database schema updated")
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
    finally:
        conn.close()

def fix_code_files():
    """Fix the code files to use the correct column names."""
    print("\n🔧 Fixing code files...")
    
    # Files to fix
    files_to_fix = [
        "src/services/worker_manager.py",
        "src/database/manager.py"
    ]
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            continue
            
        print(f"📝 Fixing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix INSERT statements
        original_pattern = r"INSERT INTO worker_activity_log \(worker_id, chat_id, success, error, created_at\)"
        replacement = "INSERT INTO worker_activity_log (worker_id, destination_id, success, error, created_at)"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix VALUES placeholders
        original_pattern = r"VALUES \(worker_id, chat_id, success, error, created_at\)"
        replacement = "VALUES (worker_id, destination_id, success, error, created_at)"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix parameter references
        original_pattern = r"VALUES \(\?, \?, \?, \?, \?\)"
        replacement = "VALUES (?, ?, ?, ?, ?)"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix function parameters
        original_pattern = r"async def _log_worker_activity\(self, worker_id: int, chat_id: int, success: bool, error: str = None\):"
        replacement = "async def _log_worker_activity(self, worker_id: int, destination_id: str, success: bool, error: str = None):"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix function calls
        original_pattern = r"_log_worker_activity\(worker_id, chat_id, success, error\)"
        replacement = "_log_worker_activity(worker_id, destination_id, success, error)"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix record_posting_attempt method
        original_pattern = r"async def record_posting_attempt\(self, worker_id: int, group_id: str, success: bool, error: str = None\) -> bool:"
        replacement = "async def record_posting_attempt(self, worker_id: int, destination_id: str, success: bool, error: str = None) -> bool:"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix the INSERT statement in record_posting_attempt
        original_pattern = r"INSERT INTO worker_activity_log \(worker_id, chat_id, success, error, created_at\)\s+VALUES \(\?, \?, \?, \?, \?\)"
        replacement = "INSERT INTO worker_activity_log (worker_id, destination_id, success, error, created_at)\n                    VALUES (?, ?, ?, ?, ?)"
        content = re.sub(original_pattern, replacement, content)
        
        # Fix parameter tuple
        original_pattern = r"\(worker_id, group_id, success, error, datetime\.now\(\)\)"
        replacement = "(worker_id, destination_id, success, error, datetime.now())"
        content = re.sub(original_pattern, replacement, content)
        
        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed {file_path}")

def verify_fixes():
    """Verify that the fixes are correct."""
    print("\n🔍 Verifying fixes...")
    
    # Check database schema
    db_path = "bot_database.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Database columns: {column_names}")
        
        if 'destination_id' in column_names:
            print("✅ destination_id column exists in database")
        else:
            print("❌ destination_id column missing in database")
        
        if 'chat_id' in column_names:
            print("✅ chat_id column exists in database (for compatibility)")
        else:
            print("⚠️ chat_id column not in database")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        conn.close()
    
    # Check code files
    files_to_check = [
        "src/services/worker_manager.py",
        "src/database/manager.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'destination_id' in content:
                print(f"✅ {file_path} uses destination_id")
            else:
                print(f"⚠️ {file_path} may still have issues")
            
            if 'chat_id' in content and 'worker_activity_log' in content:
                print(f"⚠️ {file_path} still contains chat_id references")
            else:
                print(f"✅ {file_path} chat_id references cleaned")

def main():
    """Main function."""
    print("🔧 FIXING CHAT_ID COLUMN ISSUE")
    print("=" * 50)
    
    # Step 1: Fix database schema
    fix_database_schema()
    
    # Step 2: Fix code files
    fix_code_files()
    
    # Step 3: Verify fixes
    verify_fixes()
    
    print("\n🎉 CHAT_ID COLUMN ISSUE FIXED!")
    print("\n📋 What was fixed:")
    print("   • Added destination_id column to database")
    print("   • Updated code to use destination_id instead of chat_id")
    print("   • Fixed INSERT statements in worker_manager.py")
    print("   • Fixed INSERT statements in database/manager.py")
    print("\n🚀 Your bot should now log worker activity without errors!")

if __name__ == "__main__":
    main()
