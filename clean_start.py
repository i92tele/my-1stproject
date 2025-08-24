#!/usr/bin/env python3
"""
Clean Start Script
Deletes all ads, test users, and related data for a fresh beta launch
"""

import os
import sys
import sqlite3
import asyncio
import logging

def load_env_file():
    """Load .env file manually"""
    possible_paths = ['.env', 'config/.env', 'config/env_template.txt']
    for env_file in possible_paths:
        if os.path.exists(env_file):
            print(f"📁 Found .env file at: {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
    return False

def get_database_connection():
    """Get database connection"""
    db_path = os.getenv('DATABASE_URL', 'bot_database.db')
    if db_path.startswith('sqlite:///'):
        db_path = db_path[10:]  # Remove sqlite:/// prefix
    elif db_path.startswith('sqlite://'):
        db_path = db_path[9:]   # Remove sqlite:// prefix
    
    print(f"📁 Database path: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return None
    
    return sqlite3.connect(db_path)

def show_current_data(conn):
    """Show current data before cleanup"""
    cursor = conn.cursor()
    
    print("\n📊 Current Data Summary:")
    print("=" * 40)
    
    # Count users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"👥 Users: {user_count}")
    
    # Count ad slots
    cursor.execute("SELECT COUNT(*) FROM ad_slots")
    ad_count = cursor.fetchone()[0]
    print(f"📢 Ad Slots: {ad_count}")
    
    # Count payments
    cursor.execute("SELECT COUNT(*) FROM payments")
    payment_count = cursor.fetchone()[0]
    print(f"💰 Payments: {payment_count}")
    
    # Count suggestions
    cursor.execute("SELECT COUNT(*) FROM suggestions")
    suggestion_count = cursor.fetchone()[0]
    print(f"💡 Suggestions: {suggestion_count}")
    
    # Count failed groups
    cursor.execute("SELECT COUNT(*) FROM failed_groups")
    failed_group_count = cursor.fetchone()[0]
    print(f"❌ Failed Groups: {failed_group_count}")
    
    # Show some sample data
    print("\n📋 Sample Data:")
    
    # Sample users
    cursor.execute("SELECT user_id, username, subscription_tier, created_at FROM users LIMIT 5")
    users = cursor.fetchall()
    if users:
        print("👥 Sample Users:")
        for user in users:
            print(f"  - User {user[0]} (@{user[1] or 'No username'}) - {user[2]} - {user[3]}")
    
    # Sample ad slots
    cursor.execute("SELECT slot_id, user_id, category, status FROM ad_slots LIMIT 5")
    ad_slots = cursor.fetchall()
    if ad_slots:
        print("📢 Sample Ad Slots:")
        for slot in ad_slots:
            print(f"  - Slot {slot[0]} (User {slot[1]}) - {slot[2]} - {slot[3]}")

def cleanup_database(conn, confirm=True):
    """Clean up all data from database"""
    cursor = conn.cursor()
    
    print("\n🧹 Starting Database Cleanup...")
    print("=" * 40)
    
    # Store counts for summary
    counts = {}
    
    # Delete ad slots first (foreign key dependency)
    cursor.execute("SELECT COUNT(*) FROM ad_slots")
    ad_count = cursor.fetchone()[0]
    if ad_count > 0:
        print(f"🗑️  Deleting {ad_count} ad slots...")
        cursor.execute("DELETE FROM ad_slots")
        counts['ad_slots'] = ad_count
    
    # Delete payments
    cursor.execute("SELECT COUNT(*) FROM payments")
    payment_count = cursor.fetchone()[0]
    if payment_count > 0:
        print(f"🗑️  Deleting {payment_count} payments...")
        cursor.execute("DELETE FROM payments")
        counts['payments'] = payment_count
    
    # Delete suggestions
    cursor.execute("SELECT COUNT(*) FROM suggestions")
    suggestion_count = cursor.fetchone()[0]
    if suggestion_count > 0:
        print(f"🗑️  Deleting {suggestion_count} suggestions...")
        cursor.execute("DELETE FROM suggestions")
        counts['suggestions'] = suggestion_count
    
    # Delete failed groups
    cursor.execute("SELECT COUNT(*) FROM failed_groups")
    failed_group_count = cursor.fetchone()[0]
    if failed_group_count > 0:
        print(f"🗑️  Deleting {failed_group_count} failed groups...")
        cursor.execute("DELETE FROM failed_groups")
        counts['failed_groups'] = failed_group_count
    
    # Delete users (this will also clean up any remaining references)
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    if user_count > 0:
        print(f"🗑️  Deleting {user_count} users...")
        cursor.execute("DELETE FROM users")
        counts['users'] = user_count
    
    # Commit changes
    conn.commit()
    
    print("\n✅ Cleanup Summary:")
    print("=" * 20)
    for table, count in counts.items():
        print(f"🗑️  Deleted {count} records from {table}")
    
    if not counts:
        print("✨ Database was already clean!")
    
    return counts

def verify_cleanup(conn):
    """Verify that cleanup was successful"""
    cursor = conn.cursor()
    
    print("\n🔍 Verifying Cleanup...")
    print("=" * 30)
    
    tables = ['users', 'ad_slots', 'payments', 'suggestions', 'failed_groups']
    all_clean = True
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            print(f"✅ {table}: Clean ({count} records)")
        else:
            print(f"❌ {table}: Still has {count} records")
            all_clean = False
    
    if all_clean:
        print("\n🎉 All tables are clean!")
        return True
    else:
        print("\n⚠️  Some tables still have data")
        return False

def reset_auto_increment(conn):
    """Reset auto-increment counters"""
    cursor = conn.cursor()
    
    print("\n🔄 Resetting Auto-increment Counters...")
    print("=" * 40)
    
    # Reset SQLite sequence for each table
    tables_with_auto_increment = ['users', 'ad_slots', 'payments', 'suggestions', 'failed_groups']
    
    for table in tables_with_auto_increment:
        try:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            print(f"✅ Reset counter for {table}")
        except Exception as e:
            print(f"⚠️  Could not reset counter for {table}: {e}")
    
    conn.commit()
    print("✅ Auto-increment counters reset")

def main():
    """Main cleanup function"""
    print("🧹 Clean Start Script")
    print("=" * 50)
    print("This will delete ALL data from the database for a fresh start.")
    print("⚠️  WARNING: This action cannot be undone!")
    print()
    
    if not load_env_file():
        print("❌ Could not load .env file")
        return False
    
    # Get database connection
    conn = get_database_connection()
    if not conn:
        return False
    
    try:
        # Show current data
        show_current_data(conn)
        
        # Ask for confirmation
        print("\n" + "=" * 50)
        response = input("❓ Are you sure you want to delete ALL data? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("❌ Cleanup cancelled")
            return False
        
        # Perform cleanup
        counts = cleanup_database(conn)
        
        # Reset auto-increment counters
        reset_auto_increment(conn)
        
        # Verify cleanup
        is_clean = verify_cleanup(conn)
        
        if is_clean:
            print("\n🎉 CLEAN START COMPLETE!")
            print("=" * 30)
            print("✅ All data deleted")
            print("✅ Auto-increment counters reset")
            print("✅ Database ready for beta launch")
            print("\n🚀 You can now start fresh with beta users!")
        else:
            print("\n⚠️  Cleanup may not be complete")
            print("Please check the verification results above")
        
        return is_clean
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
