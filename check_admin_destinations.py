#!/usr/bin/env python3
"""
Admin Destinations Diagnostic Tool

This script checks the admin slot destinations in the database and diagnoses
any issues with how they're being stored or retrieved.
"""

import asyncio
import sqlite3
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "bot_database.db"

class AdminDestinationDiagnostic:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def get_admin_slots(self) -> List[Dict[str, Any]]:
        """Get all admin ad slots."""
        self.cursor.execute('''
            SELECT * FROM admin_ad_slots 
            ORDER BY slot_number
        ''')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_admin_slot_destinations(self, slot_id: int) -> List[Dict[str, Any]]:
        """Get destinations for a specific admin ad slot by ID."""
        self.cursor.execute('''
            SELECT * FROM admin_slot_destinations 
            WHERE slot_id = ?
            ORDER BY id
        ''', (slot_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_admin_slot_by_number(self, slot_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific admin ad slot by slot number."""
        self.cursor.execute('''
            SELECT * FROM admin_ad_slots 
            WHERE slot_number = ?
        ''', (slot_number,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def check_tables_exist(self) -> Dict[str, bool]:
        """Check if required tables exist."""
        tables = ['admin_ad_slots', 'admin_slot_destinations']
        results = {}
        
        for table in tables:
            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            results[table] = bool(self.cursor.fetchone())
        
        return results
    
    def check_schema(self) -> Dict[str, List[str]]:
        """Check the schema of the admin tables."""
        results = {}
        
        for table in ['admin_ad_slots', 'admin_slot_destinations']:
            try:
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = [row['name'] for row in self.cursor.fetchall()]
                results[table] = columns
            except Exception as e:
                results[table] = [f"Error: {str(e)}"]
        
        return results
    
    def add_test_destination(self, slot_number: int, destination_id: str, destination_name: str) -> bool:
        """Add a test destination to an admin slot."""
        # First get the slot_id from the slot_number
        slot = self.get_admin_slot_by_number(slot_number)
        if not slot:
            print(f"❌ Admin slot {slot_number} not found")
            return False
        
        slot_id = slot['id']
        
        try:
            # Check if destination already exists
            self.cursor.execute('''
                SELECT id FROM admin_slot_destinations 
                WHERE slot_id = ? AND destination_id = ?
            ''', (slot_id, destination_id))
            
            if self.cursor.fetchone():
                print(f"ℹ️ Destination {destination_id} already exists for slot {slot_number}")
                return True
            
            # Insert new destination
            self.cursor.execute('''
                INSERT INTO admin_slot_destinations 
                (slot_id, destination_type, destination_id, destination_name, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                slot_id,
                'group',
                destination_id,
                destination_name,
                1,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            print(f"✅ Added destination {destination_id} to slot {slot_number}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding destination: {e}")
            return False
    
    def run_diagnostics(self):
        """Run all diagnostics."""
        print("\n🔍 ADMIN DESTINATIONS DIAGNOSTIC")
        print("=" * 60)
        
        # Check if tables exist
        print("\n📊 CHECKING DATABASE TABLES")
        print("-" * 40)
        tables = self.check_tables_exist()
        for table, exists in tables.items():
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"{table}: {status}")
        
        # Check schema
        print("\n📋 CHECKING TABLE SCHEMA")
        print("-" * 40)
        schema = self.check_schema()
        for table, columns in schema.items():
            print(f"{table} columns:")
            for col in columns:
                print(f"  - {col}")
        
        # Check admin slots
        print("\n📦 ADMIN SLOTS")
        print("-" * 40)
        admin_slots = self.get_admin_slots()
        if not admin_slots:
            print("❌ No admin slots found")
        else:
            print(f"✅ Found {len(admin_slots)} admin slots")
            for slot in admin_slots:
                active = "✅ ACTIVE" if slot.get('is_active') else "❌ INACTIVE"
                print(f"Slot #{slot.get('slot_number')}: ID={slot.get('id')} - {active}")
                print(f"  Content: {slot.get('content', 'None')[:50]}...")
                
                # Check destinations for this slot
                destinations = self.get_admin_slot_destinations(slot.get('id'))
                if not destinations:
                    print(f"  ❌ No destinations found for slot #{slot.get('slot_number')}")
                else:
                    print(f"  ✅ Found {len(destinations)} destinations")
                    for i, dest in enumerate(destinations[:5]):  # Show first 5 only
                        print(f"    {i+1}. {dest.get('destination_name', 'Unknown')} ({dest.get('destination_id', 'Unknown')})")
                    
                    if len(destinations) > 5:
                        print(f"    ... and {len(destinations) - 5} more")
        
        print("\n🔍 DIAGNOSTIC COMPLETE")
        print("=" * 60)

def main():
    # Check if database file exists
    try:
        with open(DB_PATH, 'rb'):
            pass
    except FileNotFoundError:
        print(f"❌ Database file not found: {DB_PATH}")
        print("Please specify the correct database path.")
        sys.exit(1)
    
    # Run diagnostics
    diagnostic = AdminDestinationDiagnostic(DB_PATH)
    diagnostic.connect()
    diagnostic.run_diagnostics()
    
    # Ask if user wants to add a test destination
    print("\n🔧 WOULD YOU LIKE TO ADD A TEST DESTINATION?")
    print("This can help diagnose destination issues.")
    choice = input("Add test destination? (y/n): ")
    
    if choice.lower() == 'y':
        slot_number = int(input("Enter slot number (1-5): "))
        destination_id = input("Enter destination ID (e.g. @channel): ")
        destination_name = input("Enter destination name: ")
        
        diagnostic.add_test_destination(slot_number, destination_id, destination_name)
    
    diagnostic.close()

if __name__ == "__main__":
    main()
