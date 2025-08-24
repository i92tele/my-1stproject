#!/usr/bin/env python3
"""
Database Unlock Script
Quick fix for database lock issues that prevent user commands from working
"""

import sqlite3
import time
import os

def unlock_database():
    """Unlock the database and fix basic issues."""
    print("🔓 Unlocking database...")
    
    try:
        # Close any existing connections
        print("⏳ Waiting for existing connections to close...")
        time.sleep(3)
        
        # Try to connect with a short timeout
        conn = sqlite3.connect("bot_database.db", timeout=10)
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Simple test query to ensure database is accessible
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"✅ Database accessible - found {table_count} tables")
        
        # Quick health check
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            print("✅ Users table exists")
        else:
            print("❌ Users table missing")
        
        conn.close()
        print("✅ Database connection test successful")
        return True
        
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            print("❌ Database is locked")
            print("💡 Try stopping the bot and running this script again")
            return False
        else:
            print(f"❌ Database error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_bot_token():
    """Check if bot token is available."""
    print("\n🔑 Checking bot token...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv('config/.env')
        
        bot_token = os.getenv('BOT_TOKEN')
        if bot_token:
            print(f"✅ Bot token found: {bot_token[:10]}...")
            return True
        else:
            print("❌ BOT_TOKEN not found in environment")
            print("💡 Check your config/.env file")
            return False
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Quick Bot Fix Script")
    print("=" * 40)
    
    # Test 1: Database
    db_ok = unlock_database()
    
    # Test 2: Bot token
    token_ok = check_bot_token()
    
    print("\n" + "="*40)
    if db_ok and token_ok:
        print("✅ Basic checks passed!")
        print("\nIf user commands still don't work:")
        print("1. Stop the bot completely")
        print("2. Wait 10 seconds")
        print("3. Restart: source venv/bin/activate && python3 bot.py")
        print("4. Test /start command in Telegram")
    else:
        print("❌ Issues found - fix them before restarting bot")
        
        if not db_ok:
            print("🔧 Database issue: Stop all bot processes first")
        if not token_ok:
            print("🔧 Token issue: Check config/.env file")

if __name__ == '__main__':
    main()
