#!/usr/bin/env python3
"""
Database Migration Script
Adds new columns and tables for subscription upgrades and notifications
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def run_database_migration(db_path: str):
    """Run database migration to add new features."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting database migration...")
        
        # Check if migration has already been run
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add new columns to users table if they don't exist
        new_columns = [
            ('upgrade_history', 'TEXT'),
            ('last_upgrade_date', 'TIMESTAMP'),
            ('last_notification_date', 'TIMESTAMP'),
            ('notification_preferences', 'TEXT')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Column {col_name} might already exist: {e}")
        
        # Create admin_ad_slots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_ad_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_number INTEGER UNIQUE,
                content TEXT,
                destinations TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Created admin_ad_slots table")
        
        # Create admin_slot_posts table for tracking admin slot posts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_slot_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER,
                destination_id TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (slot_id) REFERENCES admin_ad_slots (id)
            )
        ''')
        print("✅ Created admin_slot_posts table")
        
        # Create notification_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                notification_type TEXT,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        print("✅ Created notification_log table")
        
        # Create posting_history table for comprehensive posting tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER,
                slot_type TEXT DEFAULT 'user',
                destination_id TEXT,
                destination_name TEXT,
                worker_id INTEGER,
                success BOOLEAN,
                error_message TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_content_hash TEXT,
                retry_count INTEGER DEFAULT 0,
                ban_detected BOOLEAN DEFAULT 0,
                ban_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES ad_slots(id)
            )
        ''')
        print("✅ Created posting_history table")
        
        # Create worker_bans table for tracking worker bans per destination
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worker_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                destination_id TEXT,
                ban_type TEXT,
                ban_reason TEXT,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estimated_unban_time TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Created worker_bans table")
        
        # Create destination_health table for tracking destination success rates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS destination_health (
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
        
        # Insert initial admin slots if they don't exist
        cursor.execute('SELECT COUNT(*) FROM admin_ad_slots')
        existing_slots = cursor.fetchone()[0]
        
        if existing_slots == 0:
            import json
            for i in range(1, 21):
                cursor.execute('''
                    INSERT INTO admin_ad_slots (slot_number, content, destinations, is_active)
                    VALUES (?, ?, ?, ?)
                ''', (i, None, json.dumps([]), True))
            print("✅ Created 20 initial admin ad slots")
        
        # Commit all changes
        conn.commit()
        conn.close()
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        logger.error(f"Database migration error: {e}")
        return False

async def verify_migration(db_path: str):
    """Verify that migration was successful."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Verifying migration...")
        
        # Check users table columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        required_columns = ['upgrade_history', 'last_upgrade_date', 'last_notification_date', 'notification_preferences']
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print("✅ All required columns present in users table")
        
        # Check admin_ad_slots table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
        if cursor.fetchone():
            cursor.execute('SELECT COUNT(*) FROM admin_ad_slots')
            slot_count = cursor.fetchone()[0]
            print(f"✅ admin_ad_slots table exists with {slot_count} slots")
        else:
            print("❌ admin_ad_slots table missing")
            return False
        
        # Check admin_slot_posts table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_slot_posts'")
        if cursor.fetchone():
            print("✅ admin_slot_posts table exists")
        else:
            print("❌ admin_slot_posts table missing")
            return False
        
        # Check notification_log table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notification_log'")
        if cursor.fetchone():
            print("✅ notification_log table exists")
        else:
            print("❌ notification_log table missing")
            return False
        
        conn.close()
        print("🎉 Migration verification successful!")
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        logger.error(f"Migration verification error: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    
    # Run migration
    db_path = "bot_database.db"
    
    async def main():
        success = await run_database_migration(db_path)
        if success:
            await verify_migration(db_path)
    
    asyncio.run(main())
