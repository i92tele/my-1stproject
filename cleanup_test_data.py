#!/usr/bin/env python3
"""
Cleanup Test Data

This script removes all test users and test ads from the database
"""

import sqlite3
import sys

def cleanup_test_data():
    """Remove all test data from the database."""
    try:
        print("🧹 Cleaning up test data...")
        conn = sqlite3.connect("bot_database.db")
        cursor = conn.cursor()
        
        # 1. Remove test users (user_id 123456789 or similar test IDs)
        print("\n📍 1. Cleaning up test users...")
        cursor.execute("DELETE FROM users WHERE user_id = 123456789")
        test_users_deleted = cursor.rowcount
        print(f"✅ Deleted {test_users_deleted} test users")
        
        # 2. Remove test ad slots (created by test users or with test content)
        print("\n📍 2. Cleaning up test ad slots...")
        cursor.execute("""
            DELETE FROM ad_slots 
            WHERE user_id = 123456789 
            OR content LIKE '%test%' 
            OR content LIKE '%TEST%'
            OR content LIKE '%dummy%'
        """)
        test_slots_deleted = cursor.rowcount
        print(f"✅ Deleted {test_slots_deleted} test ad slots")
        
        # 3. Remove test admin ad slots
        print("\n📍 3. Cleaning up test admin ad slots...")
        cursor.execute("""
            DELETE FROM admin_ad_slots 
            WHERE content LIKE '%test%' 
            OR content LIKE '%TEST%'
            OR content LIKE '%dummy%'
        """)
        test_admin_slots_deleted = cursor.rowcount
        print(f"✅ Deleted {test_admin_slots_deleted} test admin ad slots")
        
        # 4. Remove test payments
        print("\n📍 4. Cleaning up test payments...")
        cursor.execute("DELETE FROM payments WHERE user_id = 123456789")
        test_payments_deleted = cursor.rowcount
        print(f"✅ Deleted {test_payments_deleted} test payments")
        
        # 5. Remove test posting history
        print("\n📍 5. Cleaning up test posting history...")
        cursor.execute("DELETE FROM posting_history WHERE slot_id = 999")
        test_history_deleted = cursor.rowcount
        print(f"✅ Deleted {test_history_deleted} test posting history records")
        
        # 6. Remove test worker usage records
        print("\n📍 6. Cleaning up test worker usage...")
        cursor.execute("DELETE FROM worker_usage WHERE worker_id = 999")
        test_worker_usage_deleted = cursor.rowcount
        print(f"✅ Deleted {test_worker_usage_deleted} test worker usage records")
        
        # 7. Remove test destination health records
        print("\n📍 7. Cleaning up test destination health...")
        cursor.execute("DELETE FROM destination_health WHERE destination_id = 'test_dest'")
        test_dest_health_deleted = cursor.rowcount
        print(f"✅ Deleted {test_dest_health_deleted} test destination health records")
        
        # Commit all changes
        conn.commit()
        
        # Show remaining data
        print("\n📊 REMAINING DATA:")
        print("-" * 30)
        
        cursor.execute("SELECT COUNT(*) FROM users")
        remaining_users = cursor.fetchone()[0]
        print(f"👥 Users: {remaining_users}")
        
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE is_active = 1")
        remaining_user_slots = cursor.fetchone()[0]
        print(f"📝 User Ad Slots: {remaining_user_slots}")
        
        cursor.execute("SELECT COUNT(*) FROM admin_ad_slots WHERE is_active = 1")
        remaining_admin_slots = cursor.fetchone()[0]
        print(f"👑 Admin Ad Slots: {remaining_admin_slots}")
        
        cursor.execute("SELECT COUNT(*) FROM payments")
        remaining_payments = cursor.fetchone()[0]
        print(f"💰 Payments: {remaining_payments}")
        
        conn.close()
        
        print(f"\n🎉 Cleanup completed!")
        print(f"Total test records deleted: {test_users_deleted + test_slots_deleted + test_admin_slots_deleted + test_payments_deleted + test_history_deleted + test_worker_usage_deleted + test_dest_health_deleted}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DATA CLEANUP")
    print("=" * 60)
    
    success = cleanup_test_data()
    
    if success:
        print("\n✅ Test data cleanup completed successfully!")
    else:
        print("\n❌ Test data cleanup failed!")
    
    sys.exit(0 if success else 1)
