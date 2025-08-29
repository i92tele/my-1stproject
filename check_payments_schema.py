#!/usr/bin/env python3
"""
Check Payments Table Schema
Check the actual column names in the payments table
"""

import sqlite3
import os

def main():
    """Main function."""
    print("🔍 CHECKING PAYMENTS TABLE SCHEMA")
    print("=" * 40)
    
    try:
        db_path = "bot_database.db"
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if payments table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
        if not cursor.fetchone():
            print("❌ payments table doesn't exist")
            return
        
        print("✅ payments table exists")
        
        # Get table schema
        cursor.execute("PRAGMA table_info(payments)")
        columns = cursor.fetchall()
        
        print(f"\n📋 COLUMNS IN PAYMENTS TABLE:")
        print("-" * 40)
        for col in columns:
            col_id, name, type_name, not_null, default_val, primary_key = col
            print(f"{name} ({type_name})")
        
        # Check for cryptocurrency-related columns
        crypto_columns = [col for col in columns if 'crypto' in col[1].lower()]
        if crypto_columns:
            print(f"\n💰 CRYPTOCURRENCY COLUMNS:")
            print("-" * 40)
            for col in crypto_columns:
                print(f"✅ Found: {col[1]} ({col[2]})")
        else:
            print(f"\n❌ No cryptocurrency columns found")
            print("Available columns:")
            for col in columns:
                print(f"  - {col[1]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
