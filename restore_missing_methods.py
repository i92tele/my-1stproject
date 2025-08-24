#!/usr/bin/env python3
"""
Restore Missing Methods and Functionality

This script restores all missing methods and functionality from the recycle bin
to their proper locations in the current active files.
"""

import os
import shutil
import sqlite3
from datetime import datetime

def restore_missing_methods():
    """Restore all missing methods and functionality."""
    print("🔧 RESTORING MISSING METHODS AND FUNCTIONALITY")
    print("=" * 60)
    
    # Track restoration progress
    restored_items = []
    errors = []
    
    try:
        # 1. Restore missing database methods
        print("\n📊 1. Restoring Database Methods...")
        restore_database_methods(restored_items, errors)
        
        # 2. Restore missing tables
        print("\n🗄️ 2. Restoring Missing Tables...")
        restore_missing_tables(restored_items, errors)
        
        # 3. Restore admin commands functionality
        print("\n👨‍💼 3. Restoring Admin Commands...")
        restore_admin_commands(restored_items, errors)
        
        # 4. Restore user commands functionality
        print("\n👤 4. Restoring User Commands...")
        restore_user_commands(restored_items, errors)
        
        # 5. Restore config functionality
        print("\n⚙️ 5. Restoring Config Functionality...")
        restore_config_functionality(restored_items, errors)
        
        # 6. Verify restoration
        print("\n✅ 6. Verifying Restoration...")
        verify_restoration(restored_items, errors)
        
        # Generate report
        print("\n" + "=" * 60)
        print("📊 RESTORATION REPORT")
        print("=" * 60)
        
        if restored_items:
            print(f"✅ Successfully restored {len(restored_items)} items:")
            for item in restored_items:
                print(f"  • {item}")
        
        if errors:
            print(f"\n❌ {len(errors)} errors encountered:")
            for error in errors:
                print(f"  • {error}")
        
        if not errors:
            print("\n🎉 ALL RESTORATIONS COMPLETED SUCCESSFULLY!")
            print("🚀 System should now be fully functional!")
        else:
            print(f"\n⚠️ Restoration completed with {len(errors)} errors.")
            print("Please review and fix any remaining issues.")
        
    except Exception as e:
        print(f"❌ Critical error during restoration: {e}")
        errors.append(f"Critical error: {e}")

def restore_database_methods(restored_items, errors):
    """Restore missing methods to the database manager."""
    try:
        # Read the current database manager
        current_db_path = 'src/database/manager.py'
        if not os.path.exists(current_db_path):
            errors.append("Current database manager not found")
            return
        
        with open(current_db_path, 'r') as f:
            current_content = f.read()
        
        # Read the recycle bin database manager
        recycle_db_path = 'recycle_bin/database.py'
        if not os.path.exists(recycle_db_path):
            errors.append("Recycle bin database manager not found")
            return
        
        with open(recycle_db_path, 'r') as f:
            recycle_content = f.read()
        
        # Extract missing methods from recycle bin
        missing_methods = [
            'get_paused_slots',
            'get_revenue_stats', 
            'get_failed_groups',
            'get_system_status',
            'get_expired_subscriptions',
            'deactivate_expired_subscriptions'
        ]
        
        restored_count = 0
        for method_name in missing_methods:
            if method_name not in current_content:
                # Extract method from recycle bin
                method_code = extract_method_from_content(recycle_content, method_name)
                if method_code:
                    # Add method to current database manager
                    current_content = add_method_to_class(current_content, method_code)
                    restored_items.append(f"Database method: {method_name}")
                    restored_count += 1
                    print(f"  ✅ Restored: {method_name}")
                else:
                    errors.append(f"Could not extract method: {method_name}")
        
        # Write updated database manager
        with open(current_db_path, 'w') as f:
            f.write(current_content)
        
        print(f"  📊 Restored {restored_count} database methods")
        
    except Exception as e:
        errors.append(f"Error restoring database methods: {e}")

def restore_missing_tables(restored_items, errors):
    """Restore missing database tables."""
    try:
        db_path = 'bot_database.db'
        if not os.path.exists(db_path):
            errors.append("Database file not found")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Define missing tables and their schemas
        missing_tables = {
            'subscriptions': '''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    payment_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''',
            'payments': '''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT,
                    transaction_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''',
            'admin_ad_slots': '''
                CREATE TABLE IF NOT EXISTS admin_ad_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_number INTEGER NOT NULL,
                    content TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'failed_group_joins': '''
                CREATE TABLE IF NOT EXISTS failed_group_joins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    worker_id INTEGER,
                    error_message TEXT,
                    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0
                )
            '''
        }
        
        restored_count = 0
        for table_name, schema in missing_tables.items():
            try:
                # Check if table exists
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if not cursor.fetchone():
                    cursor.execute(schema)
                    restored_items.append(f"Database table: {table_name}")
                    restored_count += 1
                    print(f"  ✅ Created table: {table_name}")
                else:
                    print(f"  ℹ️ Table already exists: {table_name}")
            except Exception as e:
                errors.append(f"Error creating table {table_name}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"  📊 Restored {restored_count} database tables")
        
    except Exception as e:
        errors.append(f"Error restoring database tables: {e}")

def restore_admin_commands(restored_items, errors):
    """Restore missing admin commands functionality."""
    try:
        # Read current admin commands
        current_admin_path = 'commands/admin_commands.py'
        if not os.path.exists(current_admin_path):
            errors.append("Current admin commands not found")
            return
        
        with open(current_admin_path, 'r') as f:
            current_content = f.read()
        
        # Read recycle bin admin commands
        recycle_admin_path = 'recycle_bin/admin_commands.py'
        if not os.path.exists(recycle_admin_path):
            errors.append("Recycle bin admin commands not found")
            return
        
        with open(recycle_admin_path, 'r') as f:
            recycle_content = f.read()
        
        # Extract missing admin methods
        missing_admin_methods = [
            'get_admin_stats',
            'get_posting_stats',
            'get_system_status',
            'get_revenue_stats',
            'get_failed_groups'
        ]
        
        restored_count = 0
        for method_name in missing_admin_methods:
            if method_name not in current_content:
                method_code = extract_method_from_content(recycle_content, method_name)
                if method_code:
                    current_content = add_method_to_class(current_content, method_code)
                    restored_items.append(f"Admin method: {method_name}")
                    restored_count += 1
                    print(f"  ✅ Restored: {method_name}")
                else:
                    errors.append(f"Could not extract admin method: {method_name}")
        
        # Write updated admin commands
        with open(current_admin_path, 'w') as f:
            f.write(current_content)
        
        print(f"  📊 Restored {restored_count} admin methods")
        
    except Exception as e:
        errors.append(f"Error restoring admin commands: {e}")

def restore_user_commands(restored_items, errors):
    """Restore missing user commands functionality."""
    try:
        # Read current user commands
        current_user_path = 'commands/user_commands.py'
        if not os.path.exists(current_user_path):
            errors.append("Current user commands not found")
            return
        
        with open(current_user_path, 'r') as f:
            current_content = f.read()
        
        # Read recycle bin user commands
        recycle_user_path = 'recycle_bin/user_commands.py'
        if not os.path.exists(recycle_user_path):
            errors.append("Recycle bin user commands not found")
            return
        
        with open(recycle_user_path, 'r') as f:
            recycle_content = f.read()
        
        # Extract missing user methods
        missing_user_methods = [
            'show_crypto_selection',
            'handle_subscription',
            'process_payment'
        ]
        
        restored_count = 0
        for method_name in missing_user_methods:
            if method_name not in current_content:
                method_code = extract_method_from_content(recycle_content, method_name)
                if method_code:
                    current_content = add_method_to_class(current_content, method_code)
                    restored_items.append(f"User method: {method_name}")
                    restored_count += 1
                    print(f"  ✅ Restored: {method_name}")
                else:
                    errors.append(f"Could not extract user method: {method_name}")
        
        # Write updated user commands
        with open(current_user_path, 'w') as f:
            f.write(current_content)
        
        print(f"  📊 Restored {restored_count} user methods")
        
    except Exception as e:
        errors.append(f"Error restoring user commands: {e}")

def restore_config_functionality(restored_items, errors):
    """Restore missing config functionality."""
    try:
        # Check if config file exists
        config_path = 'config.py'
        if not os.path.exists(config_path):
            # Create basic config file
            config_content = '''
import os
from src.config.main_config import BotConfig

# Load configuration
config = BotConfig.load_from_env()
'''
            with open(config_path, 'w') as f:
                f.write(config_content)
            restored_items.append("Config file: config.py")
            print("  ✅ Created: config.py")
        
        # Ensure main_config.py has crypto address method
        main_config_path = 'src/config/main_config.py'
        if os.path.exists(main_config_path):
            with open(main_config_path, 'r') as f:
                config_content = f.read()
            
            if 'get_crypto_address' not in config_content:
                # Add crypto address method
                crypto_method = '''
    def get_crypto_address(self, crypto: str) -> Optional[str]:
        """Get cryptocurrency wallet address."""
        address_map = {
            'BTC': self.btc_address,
            'ETH': self.eth_address,
            'SOL': self.sol_address,
            'LTC': self.ltc_address,
            'TON': self.ton_address,
            'USDT': self.usdt_address,
            'USDC': self.usdc_address,
            'ADA': self.ada_address,
            'TRX': self.trx_address
        }
        return address_map.get(crypto.upper())
'''
                config_content = add_method_to_class(config_content, crypto_method)
                
                with open(main_config_path, 'w') as f:
                    f.write(config_content)
                
                restored_items.append("Config method: get_crypto_address")
                print("  ✅ Restored: get_crypto_address method")
        
    except Exception as e:
        errors.append(f"Error restoring config functionality: {e}")

def extract_method_from_content(content, method_name):
    """Extract a method from content."""
    try:
        # Find method start
        method_start = content.find(f"async def {method_name}(")
        if method_start == -1:
            method_start = content.find(f"def {method_name}(")
        
        if method_start == -1:
            return None
        
        # Find method end (next method or end of class)
        method_end = content.find("\n    async def ", method_start + 1)
        if method_end == -1:
            method_end = content.find("\n    def ", method_start + 1)
        if method_end == -1:
            method_end = content.find("\nclass ", method_start + 1)
        if method_end == -1:
            method_end = len(content)
        
        return content[method_start:method_end].strip()
        
    except Exception as e:
        print(f"Error extracting method {method_name}: {e}")
        return None

def add_method_to_class(content, method_code):
    """Add a method to a class."""
    try:
        # Find the last method in the class
        last_method_pos = content.rfind("\n    async def ")
        if last_method_pos == -1:
            last_method_pos = content.rfind("\n    def ")
        
        if last_method_pos == -1:
            # Add at end of class
            class_end = content.rfind("\n\n")
            if class_end == -1:
                class_end = len(content)
            return content[:class_end] + "\n\n    " + method_code + "\n" + content[class_end:]
        else:
            # Find end of last method
            method_end = content.find("\n    async def ", last_method_pos + 1)
            if method_end == -1:
                method_end = content.find("\n    def ", last_method_pos + 1)
            if method_end == -1:
                method_end = content.find("\nclass ", last_method_pos + 1)
            if method_end == -1:
                method_end = len(content)
            
            return content[:method_end] + "\n\n    " + method_code + content[method_end:]
            
    except Exception as e:
        print(f"Error adding method to class: {e}")
        return content

def verify_restoration(restored_items, errors):
    """Verify that restoration was successful."""
    try:
        print("  🔍 Verifying restoration...")
        
        # Check database methods
        db_path = 'src/database/manager.py'
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
            
            required_methods = ['get_paused_slots', 'get_revenue_stats', 'get_failed_groups']
            for method in required_methods:
                if method in content:
                    print(f"    ✅ {method} method found")
                else:
                    errors.append(f"Missing method after restoration: {method}")
        
        # Check database tables
        db_file = 'bot_database.db'
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            required_tables = ['subscriptions', 'payments', 'admin_ad_slots']
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    print(f"    ✅ {table} table found")
                else:
                    errors.append(f"Missing table after restoration: {table}")
            
            conn.close()
        
        # Check config functionality
        config_path = 'src/config/main_config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            if 'get_crypto_address' in content:
                print("    ✅ get_crypto_address method found")
            else:
                errors.append("Missing get_crypto_address method after restoration")
        
        print("  ✅ Verification completed")
        
    except Exception as e:
        errors.append(f"Error during verification: {e}")

if __name__ == "__main__":
    restore_missing_methods()

