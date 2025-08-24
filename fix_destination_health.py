#!/usr/bin/env python3
"""
Fix Destination Health Table Schema
"""

import sqlite3

def fix_destination_health():
    """Fix destination_health table schema."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔧 Fixing destination_health table schema...")
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='destination_health';")
        if not cursor.fetchone():
            print("❌ destination_health table doesn't exist, creating it...")
            cursor.execute('''
                CREATE TABLE destination_health (
                    destination_id TEXT PRIMARY KEY,
                    destination_name TEXT,
                    total_attempts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    last_success TIMESTAMP,
                    last_failure TIMESTAMP,
                    ban_count INTEGER DEFAULT 0,
                    last_ban_time TIMESTAMP,
                    cooldown_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Created destination_health table")
        else:
            print("✅ destination_health table exists")
            
            # Check current columns
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Current columns: {columns}")
            
            # Add missing columns if needed
            if 'destination_id' not in columns:
                print("❌ destination_id column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN destination_id TEXT PRIMARY KEY")
                print("✅ Added destination_id column")
            
            if 'destination_name' not in columns:
                print("❌ destination_name column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN destination_name TEXT")
                print("✅ Added destination_name column")
            
            if 'total_attempts' not in columns:
                print("❌ total_attempts column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN total_attempts INTEGER DEFAULT 0")
                print("✅ Added total_attempts column")
            
            if 'successful_posts' not in columns:
                print("❌ successful_posts column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN successful_posts INTEGER DEFAULT 0")
                print("✅ Added successful_posts column")
            
            if 'failed_posts' not in columns:
                print("❌ failed_posts column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN failed_posts INTEGER DEFAULT 0")
                print("✅ Added failed_posts column")
            
            if 'success_rate' not in columns:
                print("❌ success_rate column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN success_rate REAL DEFAULT 100.0")
                print("✅ Added success_rate column")
            
            if 'last_success' not in columns:
                print("❌ last_success column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN last_success TIMESTAMP")
                print("✅ Added last_success column")
            
            if 'last_failure' not in columns:
                print("❌ last_failure column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN last_failure TIMESTAMP")
                print("✅ Added last_failure column")
            
            if 'ban_count' not in columns:
                print("❌ ban_count column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN ban_count INTEGER DEFAULT 0")
                print("✅ Added ban_count column")
            
            if 'last_ban_time' not in columns:
                print("❌ last_ban_time column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN last_ban_time TIMESTAMP")
                print("✅ Added last_ban_time column")
            
            if 'cooldown_until' not in columns:
                print("❌ cooldown_until column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN cooldown_until TIMESTAMP")
                print("✅ Added cooldown_until column")
            
            if 'created_at' not in columns:
                print("❌ created_at column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("✅ Added created_at column")
            
            if 'updated_at' not in columns:
                print("❌ updated_at column missing, adding...")
                cursor.execute("ALTER TABLE destination_health ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("✅ Added updated_at column")
        
        # Check final schema
        cursor.execute("PRAGMA table_info(destination_health);")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"\n📋 Final columns: {final_columns}")
        
        conn.commit()
        conn.close()
        
        print("✅ Destination health table schema fixed!")
        
    except Exception as e:
        print(f"❌ Error fixing destination_health table: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_destination_health()
