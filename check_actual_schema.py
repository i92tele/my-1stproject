#!/usr/bin/env python3
"""
Check the actual database schema to see what columns exist.
"""

import sqlite3
import sys
import os

def check_actual_schema():
    """Check the actual database schema."""
    
    db_path = "bot_database.db"
    
    try:
        print("🔍 Checking actual database schema...")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check users table schema
        print("\n📊 USERS TABLE SCHEMA:")
        cursor.execute("PRAGMA table_info(users)")
        users_columns = cursor.fetchall()
        
        for col in users_columns:
            print(f"  Column {col[1]}: {col[2]} (PK: {col[5]}, NotNull: {col[3]}, Default: {col[4]})")
        
        # Check payments table schema
        print("\n💰 PAYMENTS TABLE SCHEMA:")
        cursor.execute("PRAGMA table_info(payments)")
        payments_columns = cursor.fetchall()
        
        for col in payments_columns:
            print(f"  Column {col[1]}: {col[2]} (PK: {col[5]}, NotNull: {col[3]}, Default: {col[4]})")
        
        # Check ad_slots table schema
        print("\n📺 AD_SLOTS TABLE SCHEMA:")
        cursor.execute("PRAGMA table_info(ad_slots)")
        ad_slots_columns = cursor.fetchall()
        
        for col in ad_slots_columns:
            print(f"  Column {col[1]}: {col[2]} (PK: {col[5]}, NotNull: {col[3]}, Default: {col[4]})")
        
        # Check slot_destinations table schema
        print("\n🎯 SLOT_DESTINATIONS TABLE SCHEMA:")
        cursor.execute("PRAGMA table_info(slot_destinations)")
        slot_dest_columns = cursor.fetchall()
        
        for col in slot_dest_columns:
            print(f"  Column {col[1]}: {col[2]} (PK: {col[5]}, NotNull: {col[3]}, Default: {col[4]})")
        
        conn.close()
        
        print("\n🎯 SCHEMA SUMMARY:")
        print("Now I know exactly what columns exist in each table!")
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_actual_schema()
