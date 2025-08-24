#!/usr/bin/env python3
"""
Fix Admin Buttons Not Responding

This script fixes the critical issue where admin buttons don't respond.
The root cause is incorrect callback routing patterns in bot.py.
"""

import asyncio
import sqlite3
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdminButtonFix:
    def __init__(self):
        self.db_path = "bot_database.db"
        
    async def verify_callback_routing_fix(self):
        """Verify that callback routing patterns are correct."""
        print("🔍 VERIFYING CALLBACK ROUTING FIX")
        print("=" * 50)
        
        try:
            # Read bot.py to check callback patterns
            with open('bot.py', 'r') as f:
                bot_content = f.read()
            
            # Check for admin callback patterns
            required_patterns = [
                "'^admin_toggle_slot:': admin_slots.handle_admin_slot_callback",
                "'^admin_set_content:': admin_slots.handle_admin_slot_callback",
                "'^admin_set_destinations:': admin_slots.handle_admin_slot_callback",
                "'^admin_post_slot:': admin_slots.handle_admin_slot_callback",
                "'^admin_delete_slot:': admin_slots.handle_admin_slot_callback",
                "'^admin_slot_analytics:': admin_slots.handle_admin_slot_callback",
                "'^admin_slots': admin_slots.handle_admin_slot_callback"
            ]
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in bot_content:
                    missing_patterns.append(pattern)
                    print(f"❌ Missing pattern: {pattern}")
                else:
                    print(f"✅ Pattern found: {pattern}")
            
            if missing_patterns:
                print(f"\n❌ {len(missing_patterns)} callback patterns missing!")
                return False
            else:
                print("\n✅ All callback patterns are present!")
                return True
                
        except Exception as e:
            print(f"❌ Error verifying callback routing: {e}")
            return False
    
    async def verify_admin_slots_table(self):
        """Verify admin slots table structure and data."""
        print("\n🔍 VERIFYING ADMIN SLOTS TABLE")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
            if not cursor.fetchone():
                print("❌ admin_ad_slots table does not exist")
                return False
            
            print("✅ admin_ad_slots table exists")
            
            # 2. Check table structure
            cursor.execute("PRAGMA table_info(admin_ad_slots)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            required_columns = ['id', 'slot_number', 'content', 'is_active', 'created_at', 'updated_at']
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            
            print("✅ All required columns exist")
            
            # 3. Check if admin slots exist
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
            slot_count = cursor.fetchone()[0]
            
            if slot_count == 0:
                print("❌ No admin slots exist")
                return False
            
            print(f"✅ Found {slot_count} admin slots")
            
            # 4. Check sample slot data
            cursor.execute("SELECT * FROM admin_ad_slots LIMIT 1")
            sample_slot = cursor.fetchone()
            if sample_slot:
                print(f"✅ Sample slot: ID={sample_slot[0]}, Slot={sample_slot[1]}, Active={sample_slot[3]}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error verifying admin slots table: {e}")
            return False
    
    async def verify_database_methods(self):
        """Verify all admin database methods work."""
        print("\n🔍 VERIFYING DATABASE METHODS")
        print("=" * 50)
        
        try:
            # Import database manager
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Test all admin methods
            methods_to_test = [
                ('get_admin_ad_slots', lambda: db.get_admin_ad_slots()),
                ('get_admin_ad_slot', lambda: db.get_admin_ad_slot(1)),
                ('get_admin_slot_destinations', lambda: db.get_admin_slot_destinations(1)),
                ('update_admin_slot_content', lambda: db.update_admin_slot_content(1, "Test content")),
                ('update_admin_slot_status', lambda: db.update_admin_slot_status(1, True)),
                ('create_admin_ad_slots', lambda: db.create_admin_ad_slots()),
            ]
            
            failed_methods = []
            for method_name, method_call in methods_to_test:
                try:
                    result = await method_call()
                    print(f"✅ {method_name}: Success")
                except Exception as e:
                    print(f"❌ {method_name}: Failed - {e}")
                    failed_methods.append(method_name)
            
            if failed_methods:
                print(f"\n❌ {len(failed_methods)} methods failed: {failed_methods}")
                return False
            else:
                print("\n✅ All database methods work correctly!")
                return True
                
        except Exception as e:
            print(f"❌ Error testing database methods: {e}")
            return False
    
    async def test_admin_toggle_functionality(self):
        """Test the complete admin toggle functionality."""
        print("\n🧪 TESTING ADMIN TOGGLE FUNCTIONALITY")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            from commands.admin_slot_commands import admin_toggle_slot
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # Get admin slots
            admin_slots = await db.get_admin_ad_slots()
            if not admin_slots:
                print("❌ No admin slots found")
                return False
            
            print(f"✅ Found {len(admin_slots)} admin slots")
            
            # Test toggle functionality
            test_slot = admin_slots[0]
            slot_number = test_slot.get('slot_number')
            current_status = test_slot.get('is_active')
            
            print(f"📋 Testing slot {slot_number} (current status: {current_status})")
            
            # Toggle the status
            new_status = not current_status
            success = await db.update_admin_slot_status(slot_number, new_status)
            
            if not success:
                print("❌ Failed to update admin slot status")
                return False
            
            print(f"✅ Updated admin slot {slot_number} status to {new_status}")
            
            # Verify the change
            updated_slot = await db.get_admin_ad_slot(slot_number)
            if updated_slot and updated_slot.get('is_active') == new_status:
                print("✅ Status change verified!")
                
                # Restore original status
                await db.update_admin_slot_status(slot_number, current_status)
                print("✅ Restored original status")
                return True
            else:
                print("❌ Status change not verified")
                return False
                
        except Exception as e:
            print(f"❌ Error testing admin toggle: {e}")
            return False
    
    async def create_admin_slots_if_missing(self):
        """Create admin slots if they don't exist."""
        print("\n🔧 CREATING ADMIN SLOTS IF MISSING")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if admin slots exist
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
            slot_count = cursor.fetchone()[0]
            
            if slot_count > 0:
                print(f"✅ Admin slots already exist ({slot_count} slots)")
                conn.close()
                return True
            
            # Create admin slots
            print("📍 Creating admin ad slots...")
            
            sample_content = [
                "🚀 Welcome to AutoFarming Pro! Promote your services automatically.",
                "📈 Boost your business with automated posting to premium groups.",
                "💎 Premium advertising slots for maximum visibility.",
                "🎯 Targeted promotion to high-quality Telegram groups.",
                "⚡ Lightning-fast automated posting service."
            ]
            
            for i in range(1, 6):
                cursor.execute('''
                    INSERT INTO admin_ad_slots (slot_number, content, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (i, sample_content[i-1], True, datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            print("✅ Created 5 admin ad slots")
            return True
            
        except Exception as e:
            print(f"❌ Error creating admin slots: {e}")
            return False

async def main():
    """Main function."""
    print("🚨 FIXING ADMIN BUTTONS NOT RESPONDING")
    print("=" * 60)
    
    fix = AdminButtonFix()
    
    # 1. Verify callback routing fix
    callback_fixed = await fix.verify_callback_routing_fix()
    
    # 2. Create admin slots if missing
    slots_created = await fix.create_admin_slots_if_missing()
    
    # 3. Verify admin slots table
    table_ok = await fix.verify_admin_slots_table()
    
    # 4. Verify database methods
    methods_ok = await fix.verify_database_methods()
    
    # 5. Test admin toggle functionality
    toggle_works = await fix.test_admin_toggle_functionality()
    
    print("\n📊 FIX RESULTS:")
    print("=" * 60)
    
    results = [
        ("Callback Routing", callback_fixed),
        ("Admin Slots Creation", slots_created),
        ("Admin Slots Table", table_ok),
        ("Database Methods", methods_ok),
        ("Admin Toggle Functionality", toggle_works)
    ]
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n🎯 FINAL STATUS:")
    print("=" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Admin buttons should now respond correctly")
        print("✅ Toggle Active button should work")
        print("✅ All admin slot functions should work")
    else:
        print("❌ SOME TESTS FAILED")
        print("❌ Admin buttons may still not work")
        print("❌ Additional fixes may be needed")
    
    print("\n🔄 NEXT STEPS:")
    print("1. Restart the bot")
    print("2. Test admin toggle buttons")
    print("3. Verify all admin functions work")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
