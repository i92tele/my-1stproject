#!/usr/bin/env python3
"""
Fix Immediate Errors - Corrected Version

This script fixes the specific errors reported by the user:
1. Missing get_crypto_address method
2. Missing get_paused_slots method
3. Missing subscriptions table
4. Admin interface issues
"""

import os
import sqlite3
from datetime import datetime

def fix_immediate_errors():
    """Fix the immediate errors causing system failures."""
    print("🔧 FIXING IMMEDIATE ERRORS")
    print("=" * 50)
    
    errors_fixed = []
    errors_encountered = []
    
    try:
        # 1. Fix get_crypto_address error
        print("\n💰 1. Fixing get_crypto_address error...")
        fix_crypto_address_error(errors_fixed, errors_encountered)
        
        # 2. Fix get_paused_slots error
        print("\n📊 2. Fixing get_paused_slots error...")
        fix_paused_slots_error(errors_fixed, errors_encountered)
        
        # 3. Fix subscriptions table
        print("\n📋 3. Fixing subscriptions table...")
        fix_subscriptions_table(errors_fixed, errors_encountered)
        
        # 4. Fix admin interface issues
        print("\n👨‍💼 4. Fixing admin interface issues...")
        fix_admin_interface_issues(errors_fixed, errors_encountered)
        
        # 5. Fix config import
        print("\n⚙️ 5. Fixing config import...")
        fix_config_import(errors_fixed, errors_encountered)
        
        # 6. Verify fixes
        print("\n✅ 6. Verifying fixes...")
        verify_fixes(errors_fixed, errors_encountered)
        
        # Generate report
        print("\n" + "=" * 50)
        print("📊 FIX REPORT")
        print("=" * 50)
        
        if errors_fixed:
            print(f"✅ Fixed {len(errors_fixed)} issues:")
            for fix in errors_fixed:
                print(f"  • {fix}")
        
        if errors_encountered:
            print(f"\n❌ {len(errors_encountered)} issues remain:")
            for error in errors_encountered:
                print(f"  • {error}")
        
        if not errors_encountered:
            print("\n🎉 ALL IMMEDIATE ERRORS FIXED!")
            print("🚀 System should now be functional!")
        else:
            print(f"\n⚠️ Fixed {len(errors_fixed)} issues, {len(errors_encountered)} remain.")
        
    except Exception as e:
        print(f"❌ Critical error during fixes: {e}")

def fix_crypto_address_error(errors_fixed, errors_encountered):
    """Fix the get_crypto_address error."""
    try:
        # Check if config.py exists and has proper imports
        config_path = 'config.py'
        if not os.path.exists(config_path):
            # Create config.py
            config_content = '''import os
from src.config.main_config import BotConfig

# Load configuration
config = BotConfig.load_from_env()
'''
            with open(config_path, 'w') as f:
                f.write(config_content)
            errors_fixed.append("Created config.py with proper imports")
            print("  ✅ Created config.py")
        
        # Check if main_config.py has get_crypto_address method
        main_config_path = 'src/config/main_config.py'
        if os.path.exists(main_config_path):
            with open(main_config_path, 'r') as f:
                content = f.read()
            
            if 'get_crypto_address' not in content:
                # Add the method
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
                # Find where to insert the method
                if 'class BotConfig:' in content:
                    # Insert before the last method or at end of class
                    insert_pos = content.rfind('\n    def ')
                    if insert_pos == -1:
                        insert_pos = content.rfind('\nclass ')
                    
                    if insert_pos != -1:
                        # Find end of class
                        class_end = content.find('\nclass ', insert_pos + 1)
                        if class_end == -1:
                            class_end = len(content)
                        
                        new_content = content[:class_end] + crypto_method + '\n' + content[class_end:]
                        
                        with open(main_config_path, 'w') as f:
                            f.write(new_content)
                        
                        errors_fixed.append("Added get_crypto_address method to BotConfig")
                        print("  ✅ Added get_crypto_address method")
                    else:
                        errors_encountered.append("Could not find insertion point for get_crypto_address")
                else:
                    errors_encountered.append("BotConfig class not found in main_config.py")
            else:
                print("  ✅ get_crypto_address method already exists")
        else:
            errors_encountered.append("main_config.py not found")
            
    except Exception as e:
        errors_encountered.append(f"Error fixing crypto address: {e}")

def fix_paused_slots_error(errors_fixed, errors_encountered):
    """Fix the get_paused_slots error."""
    try:
        # Check if method exists in current database manager
        db_path = 'src/database/manager.py'
        if not os.path.exists(db_path):
            errors_encountered.append("Database manager not found")
            return
        
        with open(db_path, 'r') as f:
            content = f.read()
        
        if 'get_paused_slots' not in content:
            # Add the method from recycle bin
            paused_slots_method = '''
    async def get_paused_slots(self) -> List[Dict[str, Any]]:
        """Get all paused ad slots for monitoring."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT s.*, u.username, u.first_name FROM ad_slots s JOIN users u ON s.user_id = u.user_id WHERE s.is_paused = 1 ORDER BY s.pause_time DESC")
                slots = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return slots
            except Exception as e:
                self.logger.error(f"Error getting paused slots: {e}")
                return []
'''
            # Insert the method
            insert_pos = content.rfind('\n    async def ')
            if insert_pos == -1:
                insert_pos = content.rfind('\n    def ')
            
            if insert_pos != -1:
                # Find end of method
                method_end = content.find('\n    async def ', insert_pos + 1)
                if method_end == -1:
                    method_end = content.find('\n    def ', insert_pos + 1)
                if method_end == -1:
                    method_end = content.find('\nclass ', insert_pos + 1)
                if method_end == -1:
                    method_end = len(content)
                
                new_content = content[:method_end] + paused_slots_method + '\n' + content[method_end:]
                
                with open(db_path, 'w') as f:
                    f.write(new_content)
                
                errors_fixed.append("Added get_paused_slots method to DatabaseManager")
                print("  ✅ Added get_paused_slots method")
            else:
                errors_encountered.append("Could not find insertion point for get_paused_slots")
        else:
            print("  ✅ get_paused_slots method already exists")
            
    except Exception as e:
        errors_encountered.append(f"Error fixing paused slots: {e}")

def fix_subscriptions_table(errors_fixed, errors_encountered):
    """Fix the missing subscriptions table."""
    try:
        db_path = 'bot_database.db'
        if not os.path.exists(db_path):
            errors_encountered.append("Database file not found")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if subscriptions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'")
        if not cursor.fetchone():
            # Create subscriptions table
            cursor.execute('CREATE TABLE subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, tier TEXT NOT NULL, status TEXT DEFAULT "active", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, payment_id TEXT, FOREIGN KEY (user_id) REFERENCES users(user_id))')
            
            # Create payments table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
            if not cursor.fetchone():
                cursor.execute('CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL NOT NULL, currency TEXT NOT NULL, status TEXT DEFAULT "pending", payment_method TEXT, transaction_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id))')
            
            conn.commit()
            errors_fixed.append("Created subscriptions and payments tables")
            print("  ✅ Created subscriptions and payments tables")
        else:
            print("  ✅ subscriptions table already exists")
        
        conn.close()
        
    except Exception as e:
        errors_encountered.append(f"Error fixing subscriptions table: {e}")

def fix_admin_interface_issues(errors_fixed, errors_encountered):
    """Fix admin interface issues."""
    try:
        # Add missing admin methods to database manager
        db_path = 'src/database/manager.py'
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
            
            # Add missing admin methods
            missing_methods = {
                'get_revenue_stats': '''
    async def get_revenue_stats(self) -> Dict[str, Any]:
        """Get revenue statistics for admin dashboard."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
                total_revenue = cursor.fetchone()[0] or 0
                cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed' AND DATE(completed_at) = DATE('now')")
                today_revenue = cursor.fetchone()[0] or 0
                cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed' AND strftime('%Y-%m', completed_at) = strftime('%Y-%m', 'now')")
                monthly_revenue = cursor.fetchone()[0] or 0
                conn.close()
                return {'total_revenue': total_revenue, 'today_revenue': today_revenue, 'monthly_revenue': monthly_revenue}
            except Exception as e:
                self.logger.error(f"Error getting revenue stats: {e}")
                return {'total_revenue': 0, 'today_revenue': 0, 'monthly_revenue': 0}
''',
                'get_failed_groups': '''
    async def get_failed_groups(self) -> List[Dict[str, Any]]:
        """Get failed group joins for admin monitoring."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM failed_group_joins ORDER BY failed_at DESC LIMIT 50")
                groups = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return groups
            except Exception as e:
                self.logger.error(f"Error getting failed groups: {e}")
                return []
''',
                'get_system_status': '''
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status for admin monitoring."""
        async with self._get_lock():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
                active_slots = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM worker_usage")
                total_workers = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
                active_subscriptions = cursor.fetchone()[0]
                conn.close()
                return {'total_users': total_users, 'active_slots': active_slots, 'total_workers': total_workers, 'active_subscriptions': active_subscriptions, 'system_status': 'operational'}
            except Exception as e:
                self.logger.error(f"Error getting system status: {e}")
                return {'system_status': 'error', 'error': str(e)}
'''
            }
            
            added_count = 0
            for method_name, method_code in missing_methods.items():
                if method_name not in content:
                    # Insert method
                    insert_pos = content.rfind('\n    async def ')
                    if insert_pos == -1:
                        insert_pos = content.rfind('\n    def ')
                    
                    if insert_pos != -1:
                        method_end = content.find('\n    async def ', insert_pos + 1)
                        if method_end == -1:
                            method_end = content.find('\n    def ', insert_pos + 1)
                        if method_end == -1:
                            method_end = content.find('\nclass ', insert_pos + 1)
                        if method_end == -1:
                            method_end = len(content)
                        
                        content = content[:method_end] + method_code + '\n' + content[method_end:]
                        added_count += 1
            
            if added_count > 0:
                with open(db_path, 'w') as f:
                    f.write(content)
                
                errors_fixed.append(f"Added {added_count} admin methods to DatabaseManager")
                print(f"  ✅ Added {added_count} admin methods")
            else:
                print("  ✅ All admin methods already exist")
        
    except Exception as e:
        errors_encountered.append(f"Error fixing admin interface: {e}")

def fix_config_import(errors_fixed, errors_encountered):
    """Fix config import issues."""
    try:
        # Check if config.py has proper imports
        config_path = 'config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            if 'from src.config.main_config import BotConfig' not in content:
                # Fix the import
                config_content = '''import os
from src.config.main_config import BotConfig

# Load configuration
config = BotConfig.load_from_env()
'''
                with open(config_path, 'w') as f:
                    f.write(config_content)
                
                errors_fixed.append("Fixed config.py imports")
                print("  ✅ Fixed config.py imports")
            else:
                print("  ✅ config.py imports are correct")
        else:
            errors_encountered.append("config.py not found")
        
    except Exception as e:
        errors_encountered.append(f"Error fixing config import: {e}")

def verify_fixes(errors_fixed, errors_encountered):
    """Verify that the fixes were successful."""
    try:
        print("  🔍 Verifying fixes...")
        
        # Check get_crypto_address
        config_path = 'src/config/main_config.py'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            if 'get_crypto_address' in content:
                print("    ✅ get_crypto_address method found")
            else:
                errors_encountered.append("get_crypto_address method still missing")
        
        # Check get_paused_slots
        db_path = 'src/database/manager.py'
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
            if 'get_paused_slots' in content:
                print("    ✅ get_paused_slots method found")
            else:
                errors_encountered.append("get_paused_slots method still missing")
        
        # Check subscriptions table
        db_file = 'bot_database.db'
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'")
            if cursor.fetchone():
                print("    ✅ subscriptions table found")
            else:
                errors_encountered.append("subscriptions table still missing")
            
            conn.close()
        
        # Check admin methods
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                content = f.read()
            
            required_methods = ['get_revenue_stats', 'get_failed_groups', 'get_system_status']
            for method in required_methods:
                if method in content:
                    print(f"    ✅ {method} method found")
                else:
                    errors_encountered.append(f"{method} method still missing")
        
        # Check config import
        config_file = 'config.py'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read()
            if 'from src.config.main_config import BotConfig' in content:
                print("    ✅ config import found")
            else:
                errors_encountered.append("config import still missing")
        
        print("  ✅ Verification completed")
        
    except Exception as e:
        errors_encountered.append(f"Error during verification: {e}")

if __name__ == "__main__":
    fix_immediate_errors()

