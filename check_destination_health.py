#!/usr/bin/env python3
"""
Check and Fix Destination Health Table
"""

import sqlite3

def check_destination_health():
    """Check and fix destination_health table."""
    try:
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        print("🔍 Checking destination_health table...")
        
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
            print("✅ Created destination_health table with correct schema")
        else:
            print("✅ destination_health table exists")
            
            # Check current columns
            cursor.execute("PRAGMA table_info(destination_health);")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Current columns: {columns}")
            
            # Check if destination_id exists and is primary key
            if 'destination_id' not in columns:
                print("❌ destination_id column missing, recreating table...")
                # Drop and recreate the table
                cursor.execute("DROP TABLE destination_health")
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
                print("✅ Recreated destination_health table with correct schema")
            else:
                print("✅ destination_id column exists")
                
                # Add any missing columns
                required_columns = {
                    'destination_name': 'TEXT',
                    'total_attempts': 'INTEGER DEFAULT 0',
                    'successful_posts': 'INTEGER DEFAULT 0',
                    'failed_posts': 'INTEGER DEFAULT 0',
                    'success_rate': 'REAL DEFAULT 100.0',
                    'last_success': 'TIMESTAMP',
                    'last_failure': 'TIMESTAMP',
                    'ban_count': 'INTEGER DEFAULT 0',
                    'last_ban_time': 'TIMESTAMP',
                    'cooldown_until': 'TIMESTAMP',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                }
                
                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        try:
                            cursor.execute(f"ALTER TABLE destination_health ADD COLUMN {col_name} {col_type}")
                            print(f"  ✅ Added: {col_name}")
                        except sqlite3.OperationalError as e:
                            print(f"  ❌ Error adding {col_name}: {e}")
                    else:
                        print(f"  ℹ️ {col_name} already exists")
        
        # Check final schema
        cursor.execute("PRAGMA table_info(destination_health);")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"\n📋 Final columns: {final_columns}")
        
        # Test a simple query
        try:
            cursor.execute("SELECT COUNT(*) FROM destination_health")
            count = cursor.fetchone()[0]
            print(f"📊 Current records in destination_health: {count}")
        except Exception as e:
            print(f"❌ Error querying destination_health: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Destination health table check completed!")
        
    except Exception as e:
        print(f"❌ Error checking destination_health: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_destination_health()
