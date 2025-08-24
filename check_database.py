#!/usr/bin/env python3
"""
Check Database - See what's in the database
"""

import sqlite3
import os
from datetime import datetime

def check_database():
    """Check what's in the database."""
    db_path = "bot_database.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    print(f"✅ Database file found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\n📋 Tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Check ad_slots table
        print(f"\n📊 Ad Slots:")
        cursor.execute("SELECT COUNT(*) FROM ad_slots")
        user_slots_count = cursor.fetchone()[0]
        print(f"   User ad slots: {user_slots_count}")
        
        if user_slots_count > 0:
            cursor.execute("SELECT id, user_id, is_active, content, interval_minutes, last_sent_at FROM ad_slots LIMIT 5")
            user_slots = cursor.fetchall()
            for slot in user_slots:
                print(f"     Slot {slot[0]}: user_id={slot[1]}, active={slot[2]}, interval={slot[4]}min, last_sent={slot[5]}")
        
        # Check admin_ad_slots table
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
        admin_slots_count = cursor.fetchone()[0]
        print(f"   Admin ad slots: {admin_slots_count}")
        
        if admin_slots_count > 0:
            cursor.execute("SELECT id, is_active, content, interval_minutes, last_sent_at FROM admin_ad_slots LIMIT 5")
            admin_slots = cursor.fetchall()
            for slot in admin_slots:
                print(f"     Admin Slot {slot[0]}: active={slot[1]}, interval={slot[3]}min, last_sent={slot[4]}")
        
        # Check users table
        print(f"\n👥 Users:")
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"   Total users: {users_count}")
        
        if users_count > 0:
            cursor.execute("SELECT user_id, username, subscription_expires FROM users LIMIT 5")
            users = cursor.fetchall()
            for user in users:
                print(f"     User {user[0]}: {user[1]}, expires={user[2]}")
        
        # Check destinations
        print(f"\n🎯 Destinations:")
        cursor.execute("SELECT COUNT(*) FROM destinations")
        dest_count = cursor.fetchone()[0]
        print(f"   Total destinations: {dest_count}")
        
        # Check if any slots are due for posting
        print(f"\n⏰ Slots Due for Posting:")
        
        # Check user slots due
        cursor.execute('''
            SELECT s.id, s.user_id, s.interval_minutes, s.last_sent_at, u.username
            FROM ad_slots s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.is_active = 1 
            AND s.content IS NOT NULL 
            AND s.content != ''
            AND (u.subscription_expires IS NULL OR datetime('now') < datetime(u.subscription_expires))
            AND (
                s.last_sent_at IS NULL 
                OR datetime('now') >= datetime(s.last_sent_at, '+' || s.interval_minutes || ' minutes')
            )
        ''')
        user_due = cursor.fetchall()
        print(f"   User slots due: {len(user_due)}")
        for slot in user_due:
            print(f"     User Slot {slot[0]} (user {slot[1]}): interval={slot[2]}min, last_sent={slot[3]}")
        
        # Check admin slots due
        cursor.execute('''
            SELECT id, interval_minutes, last_sent_at
            FROM admin_ad_slots
            WHERE is_active = 1 
            AND content IS NOT NULL 
            AND content != ''
            AND (
                last_sent_at IS NULL 
                OR datetime('now') >= datetime(last_sent_at, '+' || interval_minutes || ' minutes')
            )
        ''')
        admin_due = cursor.fetchall()
        print(f"   Admin slots due: {len(admin_due)}")
        for slot in admin_due:
            print(f"     Admin Slot {slot[0]}: interval={slot[1]}min, last_sent={slot[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == '__main__':
    check_database()
