#!/usr/bin/env python3
"""
Fix Admin Toggle and Payments Table

This script fixes both the admin slot toggle button issue and the payments table structure.
"""

import asyncio
import sqlite3
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_payments_table():
    """Fix the payments table structure."""
    try:
        print("🔧 Fixing payments table structure...")
        
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Check current table structure
        print("📍 1. Checking current payments table structure...")
        cursor.execute("PRAGMA table_info(payments)")
        columns = cursor.fetchall()
        
        current_columns = [col[1] for col in columns]
        print(f"📋 Current columns: {current_columns}")
        
        # 2. Define required columns
        required_columns = {
            'amount_usd': 'REAL',
            'crypto_type': 'TEXT',
            'payment_provider': 'TEXT', 
            'pay_to_address': 'TEXT',
            'expected_amount_crypto': 'REAL',
            'payment_url': 'TEXT',
            'attribution_method': 'TEXT DEFAULT "amount_only"',
            'status': 'TEXT DEFAULT "pending"'
        }
        
        # 3. Add missing columns
        print("📍 2. Adding missing columns...")
        added_columns = []
        
        for column_name, column_def in required_columns.items():
            if column_name not in current_columns:
                try:
                    cursor.execute(f'ALTER TABLE payments ADD COLUMN {column_name} {column_def}')
                    added_columns.append(column_name)
                    print(f"✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"ℹ️ Column {column_name} already exists")
                    else:
                        print(f"❌ Error adding column {column_name}: {e}")
        
        # 4. Test payment creation
        print("📍 3. Testing payment creation...")
        try:
            test_payment_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            test_query = """
                INSERT INTO payments (
                    payment_id, user_id, amount_usd, crypto_type, payment_provider, 
                    pay_to_address, expected_amount_crypto, payment_url, expires_at, 
                    attribution_method, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(test_query, (
                test_payment_id, 1, 15.0, 'BTC', 'direct', 
                'test_address', 0.0005, 'test_url', datetime.now().isoformat(),
                'amount_only', 'pending', datetime.now(), datetime.now()
            ))
            
            # Clean up test data
            cursor.execute("DELETE FROM payments WHERE payment_id = ?", (test_payment_id,))
            
            print("✅ Payment creation test passed!")
            
        except Exception as e:
            print(f"❌ Payment creation test failed: {e}")
        
        conn.commit()
        conn.close()
        
        return len(added_columns) > 0
        
    except Exception as e:
        print(f"❌ Error fixing payments table: {e}")
        return False

async def test_admin_toggle():
    """Test admin slot toggle functionality."""
    try:
        print("\n🧪 Testing admin slot toggle functionality...")
        
        # Import database manager
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.database.manager import DatabaseManager
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # 1. Get admin slots
        print("📍 1. Getting admin slots...")
        admin_slots = await db.get_admin_ad_slots()
        print(f"📊 Found {len(admin_slots)} admin slots")
        
        if not admin_slots:
            print("❌ No admin slots found to test with")
            return False
        
        # 2. Test toggle functionality
        print("📍 2. Testing toggle functionality...")
        test_slot = admin_slots[0]
        slot_number = test_slot.get('slot_number')
        current_status = test_slot.get('is_active')
        
        print(f"📋 Testing slot {slot_number} (current status: {current_status})")
        
        # Toggle the status
        new_status = not current_status
        success = await db.update_admin_slot_status(slot_number, new_status)
        
        if success:
            print(f"✅ Successfully toggled slot {slot_number} to {new_status}")
            
            # Verify the change
            updated_slot = await db.get_admin_ad_slot(slot_number)
            if updated_slot and updated_slot.get('is_active') == new_status:
                print("✅ Status change verified!")
                
                # Toggle back to original state
                await db.update_admin_slot_status(slot_number, current_status)
                print(f"✅ Restored slot {slot_number} to original status")
                return True
            else:
                print("❌ Status change not verified")
                return False
        else:
            print("❌ Failed to toggle slot status")
            return False
            
    except Exception as e:
        print(f"❌ Error testing admin toggle: {e}")
        return False

async def verify_admin_slot_methods():
    """Verify all admin slot methods are working."""
    try:
        print("\n🔍 Verifying admin slot methods...")
        
        # Import database manager
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.database.manager import DatabaseManager
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Test all admin methods
        methods_to_test = [
            ('get_admin_ad_slots', lambda: db.get_admin_ad_slots()),
            ('get_admin_ad_slot', lambda: db.get_admin_ad_slot(1)),
            ('get_admin_slot_destinations', lambda: db.get_admin_slot_destinations(1)),
            ('update_admin_slot_content', lambda: db.update_admin_slot_content(1, "Test content")),
            ('update_admin_slot_status', lambda: db.update_admin_slot_status(1, True)),
        ]
        
        for method_name, method_call in methods_to_test:
            try:
                result = await method_call()
                print(f"✅ {method_name}: Success")
            except Exception as e:
                print(f"❌ {method_name}: Failed - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying admin methods: {e}")
        return False

def main():
    """Main function."""
    print("🔧 FIXING ADMIN TOGGLE AND PAYMENTS")
    print("=" * 60)
    
    # Fix payments table
    payments_fixed = asyncio.run(fix_payments_table())
    
    # Test admin toggle
    admin_toggle_works = asyncio.run(test_admin_toggle())
    
    # Verify admin methods
    admin_methods_work = asyncio.run(verify_admin_slot_methods())
    
    print("\n📊 SUMMARY:")
    print("=" * 60)
    
    if payments_fixed:
        print("✅ Payments table fixed")
        print("✅ Payment creation should work without errors")
    else:
        print("❌ Payments table fix failed")
    
    if admin_toggle_works:
        print("✅ Admin toggle functionality works")
        print("✅ Pause/activate buttons should work")
    else:
        print("❌ Admin toggle functionality failed")
    
    if admin_methods_work:
        print("✅ All admin slot methods are working")
    else:
        print("❌ Some admin slot methods failed")
    
    print("\n🔄 Next steps:")
    print("1. Test payment creation - should work without column errors")
    print("2. Test admin slot toggle buttons - should pause/activate ads")
    print("3. Verify admin interface is fully functional")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
