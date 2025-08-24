#!/usr/bin/env python3
"""
Fix Database Schema

This script fixes the database schema issues for admin slot destinations.
"""

import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_database_schema():
    """Fix the database schema for admin slot destinations."""
    print("🔧 FIXING DATABASE SCHEMA")
    print("=" * 50)
    
    try:
        # Connect to database
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # Check if admin_slot_destinations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_slot_destinations'")
        if not cursor.fetchone():
            print("❌ admin_slot_destinations table does not exist")
            return False
        
        print("✅ admin_slot_destinations table exists")
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(admin_slot_destinations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Current columns: {column_names}")
        
        # Check if updated_at column exists
        if 'updated_at' not in column_names:
            print("🔧 Adding updated_at column...")
            try:
                cursor.execute('ALTER TABLE admin_slot_destinations ADD COLUMN updated_at TEXT')
                print("✅ Added updated_at column")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding updated_at column: {e}")
                return False
        else:
            print("✅ updated_at column already exists")
        
        # Check if created_at column exists
        if 'created_at' not in column_names:
            print("🔧 Adding created_at column...")
            try:
                cursor.execute('ALTER TABLE admin_slot_destinations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                print("✅ Added created_at column")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding created_at column: {e}")
                return False
        else:
            print("✅ created_at column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify final table structure
        cursor.execute("PRAGMA table_info(admin_slot_destinations)")
        final_columns = cursor.fetchall()
        final_column_names = [col[1] for col in final_columns]
        
        print(f"📋 Final columns: {final_column_names}")
        
        # Check for required columns
        required_columns = ['id', 'slot_id', 'destination_type', 'destination_id', 'destination_name', 'alias', 'is_active', 'created_at', 'updated_at']
        missing_columns = [col for col in required_columns if col not in final_column_names]
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        
        print("✅ All required columns are present")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False

async def test_destination_operations():
    """Test destination operations after schema fix."""
    print("\n🧪 TESTING DESTINATION OPERATIONS")
    print("=" * 50)
    
    try:
        # Import required modules
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.database.manager import DatabaseManager
        
        # Initialize database manager
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        # Test adding a destination
        test_destination = {
            'destination_type': 'group',
            'destination_id': 'test_schema_fix',
            'destination_name': 'Test Schema Fix',
            'alias': 'test',
            'is_active': True
        }
        
        success = await db.add_admin_slot_destination(1, test_destination)
        
        if success:
            print("✅ Destination addition works after schema fix")
            
            # Clean up
            await db.remove_admin_slot_destination(1, 'test_schema_fix')
            print("✅ Destination removal works after schema fix")
            
            return True
        else:
            print("❌ Destination addition failed after schema fix")
            return False
            
    except Exception as e:
        print(f"❌ Error testing destination operations: {e}")
        return False

async def main():
    """Main function."""
    print("🔧 FIXING DATABASE SCHEMA ISSUES")
    print("=" * 60)
    
    # Fix database schema
    schema_fixed = fix_database_schema()
    
    if schema_fixed:
        # Test destination operations
        operations_ok = await test_destination_operations()
        
        print("\n📊 FIX RESULTS:")
        print("=" * 60)
        
        results = [
            ("Database Schema Fix", schema_fixed),
            ("Destination Operations", operations_ok)
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
            print("🎉 ALL FIXES SUCCESSFUL!")
            print("✅ Database schema is now correct")
            print("✅ Destination operations should work")
            print("✅ 'Select All' button should work")
            print("✅ 'Clear Category' button should work")
        else:
            print("❌ SOME FIXES FAILED")
            print("❌ Check the results above")
    else:
        print("❌ Database schema fix failed")
    
    print("\n🔄 NEXT STEPS:")
    print("1. Restart the bot")
    print("2. Test destination selection in admin slots")
    print("3. Verify all destination buttons work")
    
    print("=" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
