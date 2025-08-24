#!/usr/bin/env python3
"""
Simple Worker Database Fix

Fixes the missing columns that are preventing workers from being loaded
"""

import sqlite3
import sys

def fix_worker_database():
    """Fix missing columns in worker tables."""
    try:
        print("🔧 Fixing worker database schema...")
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Fix worker_usage table
        print("📍 Fixing worker_usage table...")
        try:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN daily_limit INTEGER DEFAULT 150")
            print("✅ Added daily_limit column")
        except sqlite3.OperationalError:
            print("✅ daily_limit column already exists")
            
        try:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN hourly_limit INTEGER DEFAULT 15")
            print("✅ Added hourly_limit column")
        except sqlite3.OperationalError:
            print("✅ hourly_limit column already exists")
            
        try:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at column")
        except sqlite3.OperationalError:
            print("✅ created_at column already exists")
            
        try:
            cursor.execute("ALTER TABLE worker_usage ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added updated_at column")
        except sqlite3.OperationalError:
            print("✅ updated_at column already exists")
        
        # Fix ad_posts table
        print("📍 Fixing ad_posts table...")
        try:
            cursor.execute("ALTER TABLE ad_posts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at column to ad_posts")
        except sqlite3.OperationalError:
            print("✅ created_at column already exists in ad_posts")
        
        # Fix worker_cooldowns table
        print("📍 Fixing worker_cooldowns table...")
        try:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN hourly_limit INTEGER DEFAULT 15")
            print("✅ Added hourly_limit column to worker_cooldowns")
        except sqlite3.OperationalError:
            print("✅ hourly_limit column already exists in worker_cooldowns")
            
        try:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN daily_limit INTEGER DEFAULT 150")
            print("✅ Added daily_limit column to worker_cooldowns")
        except sqlite3.OperationalError:
            print("✅ daily_limit column already exists in worker_cooldowns")
            
        try:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added created_at column to worker_cooldowns")
        except sqlite3.OperationalError:
            print("✅ created_at column already exists in worker_cooldowns")
            
        try:
            cursor.execute("ALTER TABLE worker_cooldowns ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added updated_at column to worker_cooldowns")
        except sqlite3.OperationalError:
            print("✅ updated_at column already exists in worker_cooldowns")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("\n✅ Database schema fixes completed!")
        print("🔄 Now restart your bot to load the workers properly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("WORKER DATABASE FIX")
    print("=" * 60)
    
    success = fix_worker_database()
    
    if success:
        print("\n✅ Fix completed successfully!")
    else:
        print("\n❌ Fix failed!")
    
    sys.exit(0 if success else 1)
