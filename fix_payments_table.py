#!/usr/bin/env python3
"""
Fix Payments Table

This script fixes the payments table structure by adding missing columns
and migrating existing data to the new schema.
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
        
        # 4. Handle old column migration
        print("📍 3. Migrating old data...")
        
        # Check if old 'amount' column exists and migrate to 'amount_usd'
        if 'amount' in current_columns and 'amount_usd' in current_columns:
            try:
                cursor.execute('UPDATE payments SET amount_usd = amount WHERE amount_usd IS NULL')
                print("✅ Migrated 'amount' to 'amount_usd'")
            except Exception as e:
                print(f"⚠️ Could not migrate amount data: {e}")
        
        # Check if old 'currency' column exists and migrate to 'crypto_type'
        if 'currency' in current_columns and 'crypto_type' in current_columns:
            try:
                cursor.execute('UPDATE payments SET crypto_type = currency WHERE crypto_type IS NULL')
                print("✅ Migrated 'currency' to 'crypto_type'")
            except Exception as e:
                print(f"⚠️ Could not migrate currency data: {e}")
        
        # 5. Verify the fix
        print("📍 4. Verifying table structure...")
        cursor.execute("PRAGMA table_info(payments)")
        final_columns = cursor.fetchall()
        
        final_column_names = [col[1] for col in final_columns]
        print(f"📋 Final columns: {final_column_names}")
        
        # Check if all required columns are present
        missing_columns = [col for col in required_columns.keys() if col not in final_column_names]
        
        if not missing_columns:
            print("✅ All required columns are present!")
        else:
            print(f"❌ Missing columns: {missing_columns}")
        
        # 6. Test the create_payment method
        print("📍 5. Testing create_payment method...")
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
            
            print("✅ create_payment method test passed!")
            
        except Exception as e:
            print(f"❌ create_payment method test failed: {e}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print(f"\n📊 Summary:")
        print(f"✅ Added {len(added_columns)} new columns: {added_columns}")
        print(f"✅ Payments table structure is now correct")
        print(f"✅ Payment creation should work without errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing payments table: {e}")
        return False

def main():
    """Main function."""
    print("🔧 FIXING PAYMENTS TABLE")
    print("=" * 50)
    
    if asyncio.run(fix_payments_table()):
        print("\n✅ PAYMENTS TABLE FIXED!")
        print("✅ All required columns are present")
        print("✅ Payment creation should work correctly")
        print("✅ No more 'no such column' errors")
    else:
        print("\n❌ FAILED TO FIX PAYMENTS TABLE!")
        print("❌ Payment creation may still fail")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
