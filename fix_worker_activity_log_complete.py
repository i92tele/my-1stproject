#!/usr/bin/env python3
"""
Fix Worker Activity Log Table Complete - Fix all missing columns and dependencies
"""

import sqlite3
import os
from datetime import datetime

def fix_worker_activity_log_complete():
    """Fix worker_activity_log table with all required columns."""
    print("🔧 Fixing worker_activity_log table completely...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current structure
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current worker_activity_log columns: {column_names}")
        
        # Required columns for the table
        required_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'worker_id': 'INTEGER NOT NULL',
            'destination_id': 'TEXT',
            'destination_name': 'TEXT',
            'action': 'TEXT',
            'success': 'BOOLEAN DEFAULT 1',
            'error_message': 'TEXT',
            'created_at': 'TEXT DEFAULT (datetime(\'now\'))'
        }
        
        # Add missing columns
        for column_name, column_type in required_columns.items():
            if column_name not in column_names:
                print(f"📝 Adding {column_name} column...")
                try:
                    cursor.execute(f"ALTER TABLE worker_activity_log ADD COLUMN {column_name} {column_type}")
                    print(f"✅ Added {column_name} column")
                except Exception as e:
                    print(f"⚠️ Could not add {column_name}: {e}")
        
        # Handle legacy columns that might conflict
        legacy_mappings = {
            'chat_id': 'destination_id',
            'error': 'error_message'
        }
        
        for old_col, new_col in legacy_mappings.items():
            if old_col in column_names and new_col in column_names:
                print(f"📝 Migrating data from {old_col} to {new_col}...")
                try:
                    # Copy data from old column to new column where new column is NULL
                    cursor.execute(f"UPDATE worker_activity_log SET {new_col} = {old_col} WHERE {new_col} IS NULL AND {old_col} IS NOT NULL")
                    print(f"✅ Migrated data from {old_col} to {new_col}")
                except Exception as e:
                    print(f"⚠️ Could not migrate {old_col}: {e}")
        
        conn.commit()
        
        # Verify final structure
        cursor.execute("PRAGMA table_info(worker_activity_log)")
        final_columns = cursor.fetchall()
        final_column_names = [col[1] for col in final_columns]
        
        print(f"📋 Final worker_activity_log columns: {final_column_names}")
        
        # Check if all required columns exist
        missing_columns = [col for col in required_columns.keys() if col not in final_column_names]
        if missing_columns:
            print(f"❌ Still missing columns: {missing_columns}")
            return False
        else:
            print("✅ worker_activity_log table structure is correct")
            return True
        
    except Exception as e:
        print(f"❌ Error fixing worker_activity_log table: {e}")
        return False
    finally:
        conn.close()

def check_dependencies():
    """Check all dependencies for worker_activity_log functionality."""
    print("\n🔧 Checking dependencies...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if worker_usage table exists and has required columns
        print("📍 Checking worker_usage table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(worker_usage)")
            worker_usage_columns = [col[1] for col in cursor.fetchall()]
            print(f"✅ worker_usage table exists with columns: {worker_usage_columns}")
            
            required_worker_usage = ['worker_id', 'messages_sent_today', 'daily_limit']
            missing_worker_usage = [col for col in required_worker_usage if col not in worker_usage_columns]
            if missing_worker_usage:
                print(f"❌ worker_usage missing columns: {missing_worker_usage}")
                return False
            else:
                print("✅ worker_usage table has all required columns")
        else:
            print("❌ worker_usage table does not exist")
            return False
        
        # Check if worker_cooldowns table exists and has required columns
        print("📍 Checking worker_cooldowns table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_cooldowns'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(worker_cooldowns)")
            worker_cooldowns_columns = [col[1] for col in cursor.fetchall()]
            print(f"✅ worker_cooldowns table exists with columns: {worker_cooldowns_columns}")
            
            required_cooldowns = ['worker_id', 'is_active', 'last_used_at']
            missing_cooldowns = [col for col in required_cooldowns if col not in worker_cooldowns_columns]
            if missing_cooldowns:
                print(f"❌ worker_cooldowns missing columns: {missing_cooldowns}")
                return False
            else:
                print("✅ worker_cooldowns table has all required columns")
        else:
            print("❌ worker_cooldowns table does not exist")
            return False
        
        # Check if posting_history table exists and has required columns
        print("📍 Checking posting_history table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(posting_history)")
            posting_history_columns = [col[1] for col in cursor.fetchall()]
            print(f"✅ posting_history table exists with columns: {posting_history_columns}")
            
            required_posting = ['ban_detected', 'ban_type', 'error_message']
            missing_posting = [col for col in required_posting if col not in posting_history_columns]
            if missing_posting:
                print(f"❌ posting_history missing columns: {missing_posting}")
                return False
            else:
                print("✅ posting_history table has all required columns")
        else:
            print("❌ posting_history table does not exist")
            return False
        
        print("✅ All dependencies are satisfied")
        return True
        
    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
        return False
    finally:
        conn.close()

def test_all_queries():
    """Test all the problematic queries to ensure they work."""
    print("\n🔧 Testing all problematic queries...")
    
    db_path = 'bot_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test 1: worker_cooldowns query (wc.is_active error)
        print("📍 Test 1: worker_cooldowns query...")
        cursor.execute('''
            SELECT 
                wc.worker_id,
                wc.is_active,
                wc.last_used_at,
                wc.created_at,
                COALESCE(wu.messages_sent_today, 0) as messages_today,
                COALESCE(wu.daily_limit, 50) as daily_limit
            FROM worker_cooldowns wc
            LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                AND wu.date = date('now')
            ORDER BY wc.worker_id
            LIMIT 5
        ''')
        workers = cursor.fetchall()
        print(f"✅ worker_cooldowns query works: {len(workers)} workers found")
        
        # Test 2: get_available_workers query
        print("📍 Test 2: get_available_workers query...")
        cursor.execute('''
            SELECT 
                wc.worker_id,
                wc.is_active,
                wc.last_used_at,
                COALESCE(wu.messages_sent_today, 0) as messages_today,
                COALESCE(wu.daily_limit, 50) as daily_limit
            FROM worker_cooldowns wc
            LEFT JOIN worker_usage wu ON wc.worker_id = wu.worker_id 
                AND wu.date = date('now')
            WHERE wc.is_active = 1 
            AND COALESCE(wu.messages_sent_today, 0) < COALESCE(wu.daily_limit, 50)
            ORDER BY wc.last_used_at ASC NULLS FIRST
            LIMIT 5
        ''')
        available_workers = cursor.fetchall()
        print(f"✅ get_available_workers query works: {len(available_workers)} available workers found")
        
        # Test 3: worker_activity_log query (destination_id error)
        print("📍 Test 3: worker_activity_log query...")
        cursor.execute('''
            SELECT destination_id, destination_name, 
                   COUNT(*) as error_count
            FROM worker_activity_log
            WHERE success = 0 
            AND created_at > datetime('now', '-24 hours')
            GROUP BY destination_id, destination_name
            HAVING error_count > 0
            ORDER BY error_count DESC
            LIMIT 5
        ''')
        problematic = cursor.fetchall()
        print(f"✅ worker_activity_log query works: {len(problematic)} problematic destinations found")
        
        # Test 4: posting_history query (ban_detected error)
        print("📍 Test 4: posting_history query...")
        cursor.execute('''
            SELECT * FROM posting_history 
            WHERE ban_detected = 1
            ORDER BY posted_at DESC
            LIMIT 5
        ''')
        banned_posts = cursor.fetchall()
        print(f"✅ posting_history query works: {len(banned_posts)} banned posts found")
        
        print("✅ All queries working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing queries: {e}")
        return False
    finally:
        conn.close()

def main():
    """Run comprehensive worker_activity_log fix."""
    print("🔧 COMPLETE WORKER ACTIVITY LOG FIX")
    print("=" * 50)
    print("⚠️  Fixing worker_activity_log table and all dependencies...")
    print("=" * 50)
    
    # Fix worker_activity_log table
    table_ok = fix_worker_activity_log_complete()
    
    # Check dependencies
    dependencies_ok = check_dependencies()
    
    # Test all queries
    queries_ok = test_all_queries()
    
    print("\n" + "=" * 50)
    print("📊 FIX RESULTS:")
    print("=" * 50)
    
    print(f"  Worker Activity Log Table: {'✅ FIXED' if table_ok else '❌ FAILED'}")
    print(f"  Dependencies: {'✅ OK' if dependencies_ok else '❌ FAILED'}")
    print(f"  All Queries: {'✅ WORKING' if queries_ok else '❌ FAILED'}")
    
    print("\n" + "=" * 50)
    if table_ok and dependencies_ok and queries_ok:
        print("🎉 ALL ERRORS FIXED!")
        print("✅ worker_activity_log table structure is correct")
        print("✅ All dependencies are satisfied")
        print("✅ All database queries working correctly")
        print("✅ No more 'wc.is_active' errors")
        print("✅ No more 'destination_id' errors")
        print("✅ No more 'ban_detected' errors")
        print("\n🚀 SAFE TO START BOT")
        print("📝 Expected behavior:")
        print("  • No more database column errors")
        print("  • Workers will be available for posting")
        print("  • Ads will be posted successfully")
    else:
        print("❌ SOME ERRORS REMAIN")
        print("⚠️  Fix the failed items before starting bot")

if __name__ == "__main__":
    main()

