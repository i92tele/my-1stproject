#!/usr/bin/env python3
"""
Comprehensive Database Schema Fix
Fix all database schema inconsistencies and standardize table structures
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSchemaFixer:
    """Comprehensive database schema fixer."""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def fix_worker_activity_log_table(self):
        """Fix worker_activity_log table with proper schema."""
        print("🔧 Fixing worker_activity_log table...")
        
        # Drop and recreate the table with proper schema
        self.cursor.execute("DROP TABLE IF EXISTS worker_activity_log")
        
        self.cursor.execute('''
            CREATE TABLE worker_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL,
                worker_phone TEXT,
                destination_id TEXT,
                destination_name TEXT,
                action TEXT DEFAULT 'post',
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                error_type TEXT,
                retry_count INTEGER DEFAULT 0,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (worker_id) REFERENCES workers(rowid)
            )
        ''')
        
        # Create indexes for better performance
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_activity_worker_id ON worker_activity_log(worker_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_activity_destination ON worker_activity_log(destination_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_activity_created_at ON worker_activity_log(created_at)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_activity_success ON worker_activity_log(success)")
        
        print("✅ worker_activity_log table fixed")
    
    def fix_workers_table(self):
        """Fix workers table with proper constraints."""
        print("🔧 Fixing workers table...")
        
        # Add unique constraint to prevent duplicates
        try:
            self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_workers_phone ON workers(phone)")
            print("✅ Added unique constraint on workers.phone")
        except Exception as e:
            print(f"⚠️ Could not add unique constraint: {e}")
        
        # Ensure is_active column exists and is boolean
        try:
            self.cursor.execute("ALTER TABLE workers ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("✅ Added is_active column to workers")
        except Exception as e:
            print(f"⚠️ is_active column already exists or error: {e}")
        
        # Add health tracking columns
        columns_to_add = [
            ('success_rate', 'REAL DEFAULT 100.0'),
            ('total_posts', 'INTEGER DEFAULT 0'),
            ('successful_posts', 'INTEGER DEFAULT 0'),
            ('failed_posts', 'INTEGER DEFAULT 0'),
            ('last_used_at', 'TIMESTAMP'),
            ('hourly_posts', 'INTEGER DEFAULT 0'),
            ('daily_posts', 'INTEGER DEFAULT 0'),
            ('hourly_limit', 'INTEGER DEFAULT 15'),
            ('daily_limit', 'INTEGER DEFAULT 150'),
            ('ban_count', 'INTEGER DEFAULT 0'),
            ('error_count', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                self.cursor.execute(f"ALTER TABLE workers ADD COLUMN {column_name} {column_def}")
                print(f"✅ Added {column_name} column to workers")
            except Exception as e:
                print(f"⚠️ {column_name} column already exists or error: {e}")
        
        print("✅ workers table fixed")
    
    def fix_admin_slot_destinations_table(self):
        """Fix admin_slot_destinations table."""
        print("🔧 Fixing admin_slot_destinations table...")
        
        # Ensure table exists with proper schema
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_slot_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                destination_type TEXT DEFAULT 'group',
                destination_id TEXT NOT NULL,
                destination_name TEXT,
                alias TEXT,
                is_active BOOLEAN DEFAULT 1,
                failure_count INTEGER DEFAULT 0,
                last_error TEXT,
                last_error_at TIMESTAMP,
                success_rate REAL DEFAULT 100.0,
                total_attempts INTEGER DEFAULT 0,
                successful_posts INTEGER DEFAULT 0,
                failed_posts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES admin_ad_slots(id)
            )
        ''')
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_slot_dest_slot_id ON admin_slot_destinations(slot_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_slot_dest_destination ON admin_slot_destinations(destination_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_slot_dest_active ON admin_slot_destinations(is_active)")
        
        print("✅ admin_slot_destinations table fixed")
    
    def fix_payments_table(self):
        """Fix payments table with proper validation."""
        print("🔧 Fixing payments table...")
        
        # Add validation columns
        columns_to_add = [
            ('amount_validated', 'BOOLEAN DEFAULT 0'),
            ('verification_attempts', 'INTEGER DEFAULT 0'),
            ('last_verification_at', 'TIMESTAMP'),
            ('verification_method', 'TEXT'),
            ('rate_limit_hits', 'INTEGER DEFAULT 0'),
            ('manual_verification', 'BOOLEAN DEFAULT 0')
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                self.cursor.execute(f"ALTER TABLE payments ADD COLUMN {column_name} {column_def}")
                print(f"✅ Added {column_name} column to payments")
            except Exception as e:
                print(f"⚠️ {column_name} column already exists or error: {e}")
        
        # Create indexes with proper error handling
        try:
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
            print("✅ Created payments status index")
        except Exception as e:
            print(f"⚠️ Could not create payments status index: {e}")
        
        # Check for cryptocurrency column before creating index
        try:
            self.cursor.execute("PRAGMA table_info(payments)")
            columns = self.cursor.fetchall()
            crypto_columns = [col[1] for col in columns if 'crypto' in col[1].lower()]
            
            if crypto_columns:
                crypto_col = crypto_columns[0]  # Use the first crypto column found
                self.cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_payments_crypto ON payments({crypto_col})")
                print(f"✅ Created payments crypto index on {crypto_col}")
            else:
                print("⚠️ No cryptocurrency column found for index creation")
        except Exception as e:
            print(f"⚠️ Could not create payments crypto index: {e}")
        
        try:
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at)")
            print("✅ Created payments created_at index")
        except Exception as e:
            print(f"⚠️ Could not create payments created_at index: {e}")
        
        print("✅ payments table fixed")
    
    def create_destination_health_table(self):
        """Create destination health tracking table."""
        print("🔧 Creating destination_health table...")
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS destination_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_id TEXT UNIQUE NOT NULL,
                destination_name TEXT,
                destination_type TEXT DEFAULT 'group',
                total_attempts INTEGER DEFAULT 0,
                successful_posts INTEGER DEFAULT 0,
                failed_posts INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 100.0,
                last_success TIMESTAMP,
                last_failure TIMESTAMP,
                failure_count INTEGER DEFAULT 0,
                consecutive_failures INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                rate_limited BOOLEAN DEFAULT 0,
                rate_limit_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_dest_health_id ON destination_health(destination_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_dest_health_success_rate ON destination_health(success_rate)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_dest_health_active ON destination_health(is_active)")
        
        print("✅ destination_health table created")
    
    def create_system_health_table(self):
        """Create system health monitoring table."""
        print("🔧 Creating system_health table...")
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                error_count INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_health_type ON system_health(check_type)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_health_status ON system_health(status)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON system_health(check_timestamp)")
        
        print("✅ system_health table created")
    
    def fix_all_tables(self):
        """Fix all database tables."""
        print("🔧 COMPREHENSIVE DATABASE SCHEMA FIX")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Fix all tables
            self.fix_workers_table()
            self.fix_worker_activity_log_table()
            self.fix_admin_slot_destinations_table()
            self.fix_payments_table()
            self.create_destination_health_table()
            self.create_system_health_table()
            
            # Commit all changes
            self.conn.commit()
            
            print("\n✅ All database schema fixes completed successfully!")
            
        except Exception as e:
            print(f"❌ Error fixing database schema: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.close()

def main():
    """Main function."""
    fixer = DatabaseSchemaFixer()
    fixer.fix_all_tables()

if __name__ == "__main__":
    main()
