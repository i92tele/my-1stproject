#!/usr/bin/env python3
"""
Verify Admin Methods

This script verifies that all required admin methods are present in the DatabaseManager class.
"""

import asyncio
import sys
import logging
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_admin_methods():
    """Verify that all admin methods are present in DatabaseManager."""
    try:
        print("🔍 Verifying admin methods in DatabaseManager...")
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # List of required admin methods
        required_methods = [
            'get_admin_ad_slots',
            'get_admin_ad_slot', 
            'get_admin_slot_destinations',
            'update_admin_slot_content',
            'update_admin_slot_status',
            'delete_admin_slot'
        ]
        
        print("📋 Checking required admin methods:")
        all_present = True
        
        for method_name in required_methods:
            if hasattr(db, method_name):
                print(f"✅ {method_name} - Present")
            else:
                print(f"❌ {method_name} - Missing")
                all_present = False
        
        if all_present:
            print("\n🎉 All admin methods are present!")
            
            # Test basic functionality
            print("\n🧪 Testing basic admin functionality...")
            
            try:
                # Test get_admin_ad_slots
                admin_slots = await db.get_admin_ad_slots()
                print(f"✅ get_admin_ad_slots(): {len(admin_slots)} slots found")
                
                # Test get_admin_ad_slot if slots exist
                if admin_slots:
                    first_slot = admin_slots[0]
                    slot_number = first_slot.get('slot_number', 1)
                    slot = await db.get_admin_ad_slot(slot_number)
                    if slot:
                        print(f"✅ get_admin_ad_slot({slot_number}): Success")
                    else:
                        print(f"⚠️ get_admin_ad_slot({slot_number}): No slot found")
                else:
                    print("ℹ️ No admin slots to test with")
                
                # Test get_admin_slot_destinations
                destinations = await db.get_admin_slot_destinations(1)
                print(f"✅ get_admin_slot_destinations(1): {len(destinations)} destinations")
                
                print("\n✅ All admin methods are working correctly!")
                return True
                
            except Exception as e:
                print(f"❌ Error testing admin methods: {e}")
                return False
        else:
            print("\n❌ Some admin methods are missing!")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying admin methods: {e}")
        return False

def main():
    """Main function."""
    print("🔧 VERIFYING ADMIN METHODS")
    print("=" * 50)
    
    if asyncio.run(verify_admin_methods()):
        print("\n✅ VERIFICATION PASSED!")
        print("✅ All admin methods are present and working")
        print("✅ Admin slot commands should now work properly")
    else:
        print("\n❌ VERIFICATION FAILED!")
        print("❌ Some admin methods are missing or not working")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
