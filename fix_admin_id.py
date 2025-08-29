#!/usr/bin/env python3
"""
Fix Admin ID
Fix the missing ADMIN_ID issue
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

def fix_admin_id():
    """Fix the missing ADMIN_ID issue."""
    print("🔧 FIXING ADMIN_ID ISSUE")
    print("=" * 50)
    
    # Check current status
    admin_id = os.getenv('ADMIN_ID')
    admin_ids = os.getenv('ADMIN_IDS')
    
    print(f"📋 Current Status:")
    print(f"  - ADMIN_ID: {admin_id or 'Not set'}")
    print(f"  - ADMIN_IDS: {admin_ids or 'Not set'}")
    
    if admin_id and admin_id != '0':
        print("✅ ADMIN_ID is properly configured")
        return
    
    if admin_ids:
        print("✅ ADMIN_IDS is configured - this should work")
        print("💡 The bot should use the first ID from ADMIN_IDS")
        return
    
    print("\n❌ No admin ID configured!")
    print("\n💡 SOLUTIONS:")
    print("1. Add ADMIN_ID to your .env file:")
    print("   ADMIN_ID=your_telegram_user_id")
    print("2. Or add ADMIN_IDS to your .env file:")
    print("   ADMIN_IDS=your_telegram_user_id,another_admin_id")
    print("\n📝 To find your Telegram user ID:")
    print("   - Send a message to @userinfobot on Telegram")
    print("   - It will reply with your user ID")
    
    # Check if we can find any user IDs in the database
    try:
        import sqlite3
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users ORDER BY created_at DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            user_id = result[0]
            print(f"\n💡 SUGGESTION: Use user ID {user_id} as admin")
            print(f"   Add to .env: ADMIN_ID={user_id}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Could not check database: {e}")

if __name__ == "__main__":
    fix_admin_id()
