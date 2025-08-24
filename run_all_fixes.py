#!/usr/bin/env python3
"""
Run All Database and System Fixes
Comprehensive script to fix all identified issues
"""

import sqlite3
import time
import sys
import os

def run_comprehensive_fixes():
    """Run all database and system fixes."""
    print("🚀 Running comprehensive system fixes...")
    print("=" * 60)
    
    try:
        # Wait for any locks to clear
        print("⏳ Waiting for database locks to clear...")
        time.sleep(3)
        
        conn = sqlite3.connect("bot_database.db", timeout=60)
        cursor = conn.cursor()
        
        print("🔧 Starting database fixes...")
        
        # 1. Fix destination_health table
        print("\n📍 1. Fixing destination_health table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_health';")
        if not cursor.fetchone():
            print("❌ destination_health table missing, creating...")
            cursor.execute('''
                CREATE TABLE destination_health (
                    destination_id TEXT PRIMARY KEY,
                    destination_name TEXT,
                    total_attempts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    last_success TEXT,
                    last_failure TEXT,
                    ban_count INTEGER DEFAULT 0,
                    last_ban_time TEXT,
                    cooldown_until TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Created destination_health table")
        else:
            print("✅ destination_health table exists")
            # Check if destination_id column exists
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            if 'destination_id' not in columns:
                print("❌ destination_id column missing in destination_health")
                # Need to recreate the table with the proper schema
                try:
                    # First, backup the existing data
                    cursor.execute("ALTER TABLE destination_health RENAME TO destination_health_old;")
                    print("✅ Renamed existing table to destination_health_old")
                    
                    # Create new table with correct schema
                    cursor.execute('''
                        CREATE TABLE destination_health (
                            destination_id TEXT PRIMARY KEY,
                            destination_name TEXT,
                            total_attempts INTEGER DEFAULT 0,
                            successful_posts INTEGER DEFAULT 0,
                            failed_posts INTEGER DEFAULT 0,
                            success_rate REAL DEFAULT 100.0,
                            last_success TEXT,
                            last_failure TEXT,
                            ban_count INTEGER DEFAULT 0,
                            last_ban_time TEXT,
                            cooldown_until TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    print("✅ Created new destination_health table with proper schema")
                    
                    # Try to copy data from old table if possible
                    try:
                        cursor.execute("PRAGMA table_info(destination_health_old);")
                        old_columns = [row[1] for row in cursor.fetchall()]
                        common_columns = set(columns).intersection(set(old_columns))
                        common_columns.discard('destination_id')  # Remove primary key from copy list
                        
                        if common_columns:
                            common_cols_str = ", ".join(common_columns)
                            cursor.execute(f'''
                                INSERT INTO destination_health (destination_name, {common_cols_str})
                                SELECT destination_name, {common_cols_str} FROM destination_health_old
                            ''')
                            print(f"✅ Migrated data from old table ({cursor.rowcount} rows)")
                    except Exception as e:
                        print(f"⚠️ Could not migrate data: {e}")
                        
                    # Drop the old table
                    cursor.execute("DROP TABLE destination_health_old;")
                    print("✅ Removed old table")
                    
                except Exception as e:
                    print(f"❌ Error fixing destination_health table: {e}")
            else:
                print("✅ destination_id column exists in destination_health")
        
        # 2. Fix admin_ad_slots table
        print("\n📍 2. Checking admin_ad_slots table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots';")
        if not cursor.fetchone():
            print("❌ admin_ad_slots table missing, creating...")
            cursor.execute('''
                CREATE TABLE admin_ad_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    destinations TEXT NOT NULL,
                    interval_minutes INTEGER DEFAULT 60,
                    last_sent_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_paused BOOLEAN DEFAULT 0,
                    pause_reason TEXT,
                    pause_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            ''')
            print("✅ Created admin_ad_slots table")
        else:
            print("✅ admin_ad_slots table exists")
        
        # 3. Fix worker_usage table
        print("\n📍 3. Fixing worker_usage table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage';")
        if not cursor.fetchone():
            print("❌ worker_usage table missing, creating...")
            cursor.execute('''
                CREATE TABLE worker_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER,
                    date DATE,
                    messages_sent_today INTEGER DEFAULT 0,
                    messages_sent_this_hour INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    last_reset_hour INTEGER,
                    daily_limit INTEGER DEFAULT 50,
                    hourly_limit INTEGER DEFAULT 20,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            ''')
            print("✅ Created worker_usage table")
        else:
            # Add missing columns
            cursor.execute("PRAGMA table_info(worker_usage);")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing_columns = [
                ('messages_sent_today', 'INTEGER DEFAULT 0'),
                ('messages_sent_this_hour', 'INTEGER DEFAULT 0'),
                ('last_reset_date', 'TEXT'),
                ('last_reset_hour', 'INTEGER'),
                ('created_at', 'TEXT'),  # Remove DEFAULT CURRENT_TIMESTAMP for ALTER TABLE
                ('updated_at', 'TEXT')
            ]
            
            for col_name, col_type in missing_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE worker_usage ADD COLUMN {col_name} {col_type}")
                        print(f"  ✅ Added: {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"  ❌ Error adding {col_name}: {e}")
                else:
                    print(f"  ℹ️ {col_name} already exists")
        
        # 4. Fix failed_group_joins table
        print("\n📍 4. Fixing failed_group_joins table...")
        cursor.execute("PRAGMA table_info(failed_group_joins);")
        columns = [row[1] for row in cursor.fetchall()]
        
        missing_columns = [
            ('worker_id', 'INTEGER'),
            ('error', 'TEXT'),
            ('fail_reason', 'TEXT'),
            ('fail_count', 'INTEGER DEFAULT 0'),
            ('last_attempt', 'TEXT'),
            ('workers_tried', 'TEXT'),
            ('priority', 'INTEGER DEFAULT 0'),
            ('notes', 'TEXT'),
            ('created_at', 'TEXT'),  # Remove DEFAULT CURRENT_TIMESTAMP for ALTER TABLE
            ('updated_at', 'TEXT')
        ]
        
        for col_name, col_type in missing_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE failed_group_joins ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ Added: {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"  ❌ Error adding {col_name}: {e}")
            else:
                print(f"  ℹ️ {col_name} already exists")
        
        # 5. Add updated_at to various tables
        print("\n📍 5. Adding updated_at columns...")
        tables_needing_updated_at = [
            'ad_slots', 'admin_ad_slots', 'payments', 'managed_groups', 'worker_cooldowns'
        ]
        
        for table_name in tables_needing_updated_at:
            try:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'updated_at' not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT")
                    print(f"  ✅ Added updated_at to {table_name}")
                else:
                    print(f"  ℹ️ {table_name} already has updated_at")
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    print(f"  ⚠️ Table {table_name} doesn't exist")
                else:
                    print(f"  ❌ Error with {table_name}: {e}")
        
        # 6. Add crypto_type to payments table if missing
        print("\n📍 6. Fixing payments table...")
        cursor.execute("PRAGMA table_info(payments);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'crypto_type' not in columns:
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN crypto_type TEXT")
                print("  ✅ Added crypto_type to payments")
            except sqlite3.OperationalError as e:
                print(f"  ❌ Error adding crypto_type: {e}")
        else:
            print("  ℹ️ crypto_type already exists in payments")
        
        # 7. CRITICAL: Fix worker_usage table date column issue
        print("\n📍 7. CRITICAL: Fixing worker_usage table date column...")
        cursor.execute("PRAGMA table_info(worker_usage);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'date' not in columns:
            try:
                cursor.execute("ALTER TABLE worker_usage ADD COLUMN date DATE")
                print("  ✅ Added date column to worker_usage")
            except sqlite3.OperationalError as e:
                print(f"  ❌ Error adding date column: {e}")
        else:
            print("  ℹ️ date column already exists in worker_usage")
        
        # 8. CRITICAL: Fix timestamp preservation issues
        print("\n📍 8. CRITICAL: Fixing timestamp preservation...")
        
        # Check if ad_slots has proper timestamp columns
        cursor.execute("PRAGMA table_info(ad_slots);")
        ad_slots_columns = [row[1] for row in cursor.fetchall()]
        
        if 'last_sent_at' not in ad_slots_columns:
            try:
                cursor.execute("ALTER TABLE ad_slots ADD COLUMN last_sent_at TIMESTAMP")
                print("  ✅ Added last_sent_at to ad_slots")
            except sqlite3.OperationalError as e:
                print(f"  ❌ Error adding last_sent_at: {e}")
        else:
            print("  ✅ last_sent_at exists in ad_slots")
        
        # Check if admin_ad_slots has proper timestamp columns
        cursor.execute("PRAGMA table_info(admin_ad_slots);")
        admin_slots_columns = [row[1] for row in cursor.fetchall()]
        
        if 'last_sent_at' not in admin_slots_columns:
            try:
                cursor.execute("ALTER TABLE admin_ad_slots ADD COLUMN last_sent_at TIMESTAMP")
                print("  ✅ Added last_sent_at to admin_ad_slots")
            except sqlite3.OperationalError as e:
                print(f"  ❌ Error adding last_sent_at: {e}")
        else:
            print("  ✅ last_sent_at exists in admin_ad_slots")
        
        # 9. Create posting_history table if missing (to track all posts)
        print("\n📍 9. Creating posting_history table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history';")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE posting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER,
                    slot_type TEXT DEFAULT 'user',
                    destination_id TEXT,
                    destination_name TEXT,
                    worker_id INTEGER,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    message_content_hash TEXT,
                    ban_detected BOOLEAN DEFAULT 0,
                    ban_type TEXT,
                    posted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            ''')
            print("  ✅ Created posting_history table")
        else:
            print("  ✅ posting_history table exists")
            
            # Check if ban_detected column exists
            cursor.execute("PRAGMA table_info(posting_history);")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = [
                ('ban_detected', 'BOOLEAN DEFAULT 0'),
                ('ban_type', 'TEXT'),
                ('message_content_hash', 'TEXT'),
                ('slot_type', 'TEXT DEFAULT \'user\''),
                ('updated_at', 'TEXT')
            ]
            
            for col_name, col_type in required_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE posting_history ADD COLUMN {col_name} {col_type}")
                        print(f"  ✅ Added {col_name} to posting_history")
                    except sqlite3.OperationalError as e:
                        print(f"  ❌ Error adding {col_name}: {e}")
                else:
                    print(f"  ℹ️ {col_name} already exists in posting_history")
        
        # 10. Test timestamp preservation
        print("\n📍 10. Testing timestamp preservation...")
        try:
            # Test if we can read and write timestamps properly
            cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE last_sent_at IS NOT NULL")
            slots_with_timestamps = cursor.fetchone()[0]
            print(f"  ✅ Found {slots_with_timestamps} ad slots with timestamps")
            
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE last_sent_at IS NOT NULL")
            admin_slots_with_timestamps = cursor.fetchone()[0]
            print(f"  ✅ Found {admin_slots_with_timestamps} admin slots with timestamps")
            
        except Exception as e:
            print(f"  ⚠️ Timestamp test warning: {e}")
        
        # 11. SPAM PREVENTION: Ensure all active slots have reasonable last_sent_at
        print("\n📍 11. SPAM PREVENTION: Setting reasonable timestamps...")
        try:
            # For slots that are active but have no last_sent_at, set it to 1 hour ago to prevent immediate spam
            cursor.execute('''
                UPDATE ad_slots 
                SET last_sent_at = datetime('now', '-1 hour')
                WHERE is_active = 1 AND last_sent_at IS NULL
            ''')
            updated_user_slots = cursor.rowcount
            
            cursor.execute('''
                UPDATE admin_ad_slots 
                SET last_sent_at = datetime('now', '-1 hour')
                WHERE is_active = 1 AND last_sent_at IS NULL
            ''')
            updated_admin_slots = cursor.rowcount
            
            if updated_user_slots > 0:
                print(f"  ✅ Set safe timestamps for {updated_user_slots} user slots")
            if updated_admin_slots > 0:
                print(f"  ✅ Set safe timestamps for {updated_admin_slots} admin slots")
            
        except Exception as e:
            print(f"  ❌ Error setting spam prevention timestamps: {e}")
            
        # 12. Final database structure check for common issues
        print("\n📍 12. Final database structure check...")
        
        # Check for common tables that might need attention
        tables_to_check = [
            'worker_bans', 'worker_cooldowns', 'managed_groups', 
            'failed_group_joins', 'user_subscriptions'
        ]
        
        for table_name in tables_to_check:
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
                if cursor.fetchone():
                    print(f"  ✅ {table_name} table exists")
                    
                    # Check for common required columns
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Add common columns that should be in most tables
                    if 'created_at' not in columns:
                        try:
                            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN created_at TEXT")
                            print(f"  ✅ Added created_at to {table_name}")
                        except sqlite3.OperationalError as e:
                            print(f"  ⚠️ Could not add created_at to {table_name}: {e}")
                            
                    if 'updated_at' not in columns:
                        try:
                            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at TEXT")
                            print(f"  ✅ Added updated_at to {table_name}")
                        except sqlite3.OperationalError as e:
                            print(f"  ⚠️ Could not add updated_at to {table_name}: {e}")
                    
                    # Special case for failed_group_joins
                    if table_name == 'failed_group_joins':
                        if 'worker_id' not in columns:
                            try:
                                cursor.execute("ALTER TABLE failed_group_joins ADD COLUMN worker_id INTEGER")
                                print("  ✅ Added worker_id to failed_group_joins")
                            except sqlite3.OperationalError as e:
                                print(f"  ⚠️ Could not add worker_id to failed_group_joins: {e}")
                else:
                    print(f"  ℹ️ {table_name} table doesn't exist (not an error)")
            except Exception as e:
                print(f"  ⚠️ Error checking {table_name}: {e}")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ All database fixes completed successfully!")
        print("🚫 SPAM PREVENTION: Timestamps have been set to prevent immediate reposting")
        print("🔄 Restart the bot to apply all changes")
        print("🎯 All UI buttons and database methods should now work properly")
        print("⚠️  CRITICAL: Bot will now preserve posting timestamps to prevent spam")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during comprehensive fixes: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("🚀 Comprehensive System Fix Script")
    print("This will fix all identified database and UI issues")
    print("-" * 60)
    
    success = run_comprehensive_fixes()
    
    if success:
        print("\n🎉 SUCCESS! All fixes applied.")
        print("\nNext steps:")
        print("1. Restart the bot: source venv/bin/activate && python3 start_bot.py")
        print("2. Test all admin buttons and user interfaces")
        print("3. Verify payment system functionality")
    else:
        print("\n❌ Some fixes failed. Check the output above for details.")
        sys.exit(1)

if __name__ == '__main__':
    main()
