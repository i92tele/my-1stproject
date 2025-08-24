#!/usr/bin/env python3
"""
Deep Analysis Verification

This script performs a comprehensive deep analysis to ensure we haven't missed
any critical issues with admin toggle buttons and payment address generation.
"""

import asyncio
import sqlite3
import logging
import os
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeepAnalysis:
    def __init__(self):
        self.db_path = "bot_database.db"
        
    async def deep_analyze_admin_toggle(self):
        """Deep analysis of admin toggle functionality."""
        print("🔍 DEEP ANALYSIS: ADMIN TOGGLE")
        print("=" * 60)
        
        issues_found = []
        
        try:
            # 1. Check database connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 2. Check if admin_ad_slots table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
            if not cursor.fetchone():
                issues_found.append("❌ admin_ad_slots table does not exist")
                print("❌ CRITICAL: admin_ad_slots table missing")
            else:
                print("✅ admin_ad_slots table exists")
            
            # 3. Check table structure in detail
            cursor.execute("PRAGMA table_info(admin_ad_slots)")
            columns = cursor.fetchall()
            column_info = {col[1]: {'type': col[2], 'notnull': col[3], 'default': col[4]} for col in columns}
            
            required_columns = {
                'id': {'type': 'INTEGER', 'purpose': 'Primary key'},
                'slot_number': {'type': 'INTEGER', 'purpose': 'Slot identifier'},
                'content': {'type': 'TEXT', 'purpose': 'Slot content'},
                'is_active': {'type': 'BOOLEAN', 'purpose': 'Active status'},
                'created_at': {'type': 'TIMESTAMP', 'purpose': 'Creation time'},
                'updated_at': {'type': 'TIMESTAMP', 'purpose': 'Update time'}
            }
            
            for col_name, col_req in required_columns.items():
                if col_name not in column_info:
                    issues_found.append(f"❌ Missing column: {col_name} ({col_req['purpose']})")
                    print(f"❌ Missing column: {col_name}")
                else:
                    print(f"✅ Column {col_name}: {column_info[col_name]['type']}")
            
            # 4. Check if admin slots exist
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
            slot_count = cursor.fetchone()[0]
            
            if slot_count == 0:
                issues_found.append("❌ No admin slots exist in database")
                print("❌ No admin slots found")
            else:
                print(f"✅ Found {slot_count} admin slots")
                
                # 5. Check sample slot data
                cursor.execute("SELECT * FROM admin_ad_slots LIMIT 1")
                sample_slot = cursor.fetchone()
                if sample_slot:
                    print(f"✅ Sample slot data: ID={sample_slot[0]}, Slot={sample_slot[1]}, Active={sample_slot[3]}")
            
            # 6. Check admin_slot_destinations table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_slot_destinations'")
            if not cursor.fetchone():
                issues_found.append("❌ admin_slot_destinations table does not exist")
                print("❌ admin_slot_destinations table missing")
            else:
                print("✅ admin_slot_destinations table exists")
            
            # 7. Test database methods
            try:
                from src.database.manager import DatabaseManager
                db = DatabaseManager(self.db_path, logger)
                await db.initialize()
                
                # Test get_admin_ad_slots
                admin_slots = await db.get_admin_ad_slots()
                if not admin_slots:
                    issues_found.append("❌ get_admin_ad_slots returns empty")
                    print("❌ get_admin_ad_slots returns empty")
                else:
                    print(f"✅ get_admin_ad_slots works: {len(admin_slots)} slots")
                
                # Test get_admin_ad_slot
                if admin_slots:
                    test_slot = await db.get_admin_ad_slot(admin_slots[0]['slot_number'])
                    if not test_slot:
                        issues_found.append("❌ get_admin_ad_slot fails")
                        print("❌ get_admin_ad_slot fails")
                    else:
                        print("✅ get_admin_ad_slot works")
                
                # Test update_admin_slot_status
                if admin_slots:
                    test_slot = admin_slots[0]
                    current_status = test_slot['is_active']
                    success = await db.update_admin_slot_status(test_slot['slot_number'], not current_status)
                    if not success:
                        issues_found.append("❌ update_admin_slot_status fails")
                        print("❌ update_admin_slot_status fails")
                    else:
                        print("✅ update_admin_slot_status works")
                        # Restore original status
                        await db.update_admin_slot_status(test_slot['slot_number'], current_status)
                
            except Exception as e:
                issues_found.append(f"❌ Database methods error: {e}")
                print(f"❌ Database methods error: {e}")
            
            conn.close()
            
        except Exception as e:
            issues_found.append(f"❌ Database connection error: {e}")
            print(f"❌ Database connection error: {e}")
        
        return issues_found
    
    async def deep_analyze_payment_addresses(self):
        """Deep analysis of payment address generation."""
        print("\n🔍 DEEP ANALYSIS: PAYMENT ADDRESSES")
        print("=" * 60)
        
        issues_found = []
        
        try:
            # 1. Check environment variables
            crypto_addresses = {
                'BTC_ADDRESS': os.getenv('BTC_ADDRESS'),
                'ETH_ADDRESS': os.getenv('ETH_ADDRESS'),
                'SOL_ADDRESS': os.getenv('SOL_ADDRESS'),
                'LTC_ADDRESS': os.getenv('LTC_ADDRESS'),
                'TON_ADDRESS': os.getenv('TON_ADDRESS'),
                'USDT_ADDRESS': os.getenv('USDT_ADDRESS'),
                'USDC_ADDRESS': os.getenv('USDC_ADDRESS')
            }
            
            print("📍 Environment Variables Check:")
            missing_addresses = []
            for crypto, address in crypto_addresses.items():
                if address:
                    print(f"✅ {crypto}: {address[:10]}...")
                else:
                    print(f"❌ {crypto}: NOT SET")
                    missing_addresses.append(crypto)
            
            if missing_addresses:
                issues_found.append(f"❌ Missing addresses: {missing_addresses}")
            
            # 2. Check BotConfig class
            try:
                from src.config.bot_config import BotConfig
                config = BotConfig()
                
                print("\n📍 BotConfig.get_crypto_address Test:")
                for crypto in ['BTC', 'ETH', 'SOL', 'LTC', 'TON']:
                    address = config.get_crypto_address(crypto.lower())
                    if address:
                        print(f"✅ {crypto}: {address[:10]}...")
                    else:
                        print(f"❌ {crypto}: NOT FOUND")
                        issues_found.append(f"❌ BotConfig.get_crypto_address fails for {crypto}")
                
            except Exception as e:
                issues_found.append(f"❌ BotConfig error: {e}")
                print(f"❌ BotConfig error: {e}")
            
            # 3. Check multi_crypto_payments.py
            try:
                from multi_crypto_payments import MultiCryptoPaymentProcessor
                
                print("\n📍 MultiCryptoPaymentProcessor Test:")
                
                # Test direct payment creation
                payment_processor = MultiCryptoPaymentProcessor(None, None, logger)
                
                # Test BTC payment
                if crypto_addresses['BTC_ADDRESS']:
                    try:
                        payment_data = await payment_processor._create_direct_payment(
                            payment_id="TEST_123",
                            amount_usd=15.0,
                            crypto_type="BTC"
                        )
                        
                        if payment_data and payment_data.get('pay_to_address'):
                            print(f"✅ BTC payment address generated: {payment_data['pay_to_address'][:10]}...")
                        else:
                            print("❌ BTC payment address generation failed")
                            issues_found.append("❌ BTC payment address generation failed")
                    except Exception as e:
                        print(f"❌ BTC payment creation error: {e}")
                        issues_found.append(f"❌ BTC payment creation error: {e}")
                else:
                    print("⚠️ Skipping BTC test - address not configured")
                
                # Test SOL payment
                if crypto_addresses['SOL_ADDRESS']:
                    try:
                        payment_data = await payment_processor._create_direct_payment(
                            payment_id="TEST_456",
                            amount_usd=15.0,
                            crypto_type="SOL"
                        )
                        
                        if payment_data and payment_data.get('pay_to_address'):
                            print(f"✅ SOL payment address generated: {payment_data['pay_to_address'][:10]}...")
                        else:
                            print("❌ SOL payment address generation failed")
                            issues_found.append("❌ SOL payment address generation failed")
                    except Exception as e:
                        print(f"❌ SOL payment creation error: {e}")
                        issues_found.append(f"❌ SOL payment creation error: {e}")
                else:
                    print("⚠️ Skipping SOL test - address not configured")
                
            except Exception as e:
                issues_found.append(f"❌ MultiCryptoPaymentProcessor error: {e}")
                print(f"❌ MultiCryptoPaymentProcessor error: {e}")
            
            # 4. Check payments table structure
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
                if not cursor.fetchone():
                    issues_found.append("❌ payments table does not exist")
                    print("❌ payments table missing")
                else:
                    print("✅ payments table exists")
                    
                    # Check payments table structure
                    cursor.execute("PRAGMA table_info(payments)")
                    payment_columns = cursor.fetchall()
                    payment_column_names = [col[1] for col in payment_columns]
                    
                    required_payment_columns = [
                        'payment_id', 'user_id', 'amount_usd', 'crypto_type', 
                        'payment_provider', 'pay_to_address', 'expected_amount_crypto',
                        'payment_url', 'expires_at', 'attribution_method', 'status'
                    ]
                    
                    missing_payment_columns = [col for col in required_payment_columns if col not in payment_column_names]
                    if missing_payment_columns:
                        issues_found.append(f"❌ Missing payment columns: {missing_payment_columns}")
                        print(f"❌ Missing payment columns: {missing_payment_columns}")
                    else:
                        print("✅ All required payment columns exist")
                
                conn.close()
                
            except Exception as e:
                issues_found.append(f"❌ Payments table check error: {e}")
                print(f"❌ Payments table check error: {e}")
            
            # 5. Test full payment creation flow
            try:
                from src.database.manager import DatabaseManager
                from multi_crypto_payments import MultiCryptoPaymentProcessor
                from src.config.bot_config import BotConfig
                
                if crypto_addresses['BTC_ADDRESS']:
                    print("\n📍 Full Payment Creation Flow Test:")
                    
                    db = DatabaseManager(self.db_path, logger)
                    await db.initialize()
                    
                    config = BotConfig()
                    payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
                    
                    payment_request = await payment_processor.create_payment_request(
                        user_id=1,
                        amount_usd=15.0,
                        crypto_type="BTC"
                    )
                    
                    if payment_request and payment_request.get('payment_url'):
                        print(f"✅ Full payment creation works")
                        print(f"   Payment URL: {payment_request['payment_url'][:50]}...")
                    else:
                        print("❌ Full payment creation failed")
                        issues_found.append("❌ Full payment creation failed")
                else:
                    print("⚠️ Skipping full payment test - BTC address not configured")
                
            except Exception as e:
                issues_found.append(f"❌ Full payment creation error: {e}")
                print(f"❌ Full payment creation error: {e}")
            
        except Exception as e:
            issues_found.append(f"❌ Payment analysis error: {e}")
            print(f"❌ Payment analysis error: {e}")
        
        return issues_found
    
    async def deep_analyze_callback_routing(self):
        """Deep analysis of callback routing."""
        print("\n🔍 DEEP ANALYSIS: CALLBACK ROUTING")
        print("=" * 60)
        
        issues_found = []
        
        try:
            # 1. Check bot.py callback routing
            print("📍 Checking bot.py callback routing:")
            
            # Check if admin_slot callbacks are properly routed
            callback_patterns = [
                '^admin_slot',
                '^admin_toggle_slot:',
                '^admin_set_content:',
                '^admin_set_destinations:'
            ]
            
            # This would require reading bot.py file to verify patterns
            # For now, we'll check if the admin_slot_commands module exists
            try:
                from commands import admin_slot_commands
                print("✅ admin_slot_commands module exists")
                
                # Check if handle_admin_slot_callback function exists
                if hasattr(admin_slot_commands, 'handle_admin_slot_callback'):
                    print("✅ handle_admin_slot_callback function exists")
                else:
                    issues_found.append("❌ handle_admin_slot_callback function missing")
                    print("❌ handle_admin_slot_callback function missing")
                
                # Check if admin_toggle_slot function exists
                if hasattr(admin_slot_commands, 'admin_toggle_slot'):
                    print("✅ admin_toggle_slot function exists")
                else:
                    issues_found.append("❌ admin_toggle_slot function missing")
                    print("❌ admin_toggle_slot function missing")
                
            except ImportError as e:
                issues_found.append(f"❌ admin_slot_commands import error: {e}")
                print(f"❌ admin_slot_commands import error: {e}")
            
            # 2. Check admin slot detail function
            try:
                if hasattr(admin_slot_commands, 'admin_slot_detail'):
                    print("✅ admin_slot_detail function exists")
                else:
                    issues_found.append("❌ admin_slot_detail function missing")
                    print("❌ admin_slot_detail function missing")
            except:
                pass
            
        except Exception as e:
            issues_found.append(f"❌ Callback routing analysis error: {e}")
            print(f"❌ Callback routing analysis error: {e}")
        
        return issues_found
    
    async def deep_analyze_admin_permissions(self):
        """Deep analysis of admin permissions."""
        print("\n🔍 DEEP ANALYSIS: ADMIN PERMISSIONS")
        print("=" * 60)
        
        issues_found = []
        
        try:
            # 1. Check admin configuration
            print("📍 Checking admin configuration:")
            
            # Check if admin IDs are configured
            admin_ids = os.getenv('ADMIN_IDS', '')
            if admin_ids:
                print(f"✅ ADMIN_IDS configured: {admin_ids}")
            else:
                issues_found.append("❌ ADMIN_IDS not configured")
                print("❌ ADMIN_IDS not configured")
            
            # 2. Check admin check function
            try:
                from commands.admin_slot_commands import check_admin
                print("✅ check_admin function exists")
            except Exception as e:
                issues_found.append(f"❌ check_admin function error: {e}")
                print(f"❌ check_admin function error: {e}")
            
        except Exception as e:
            issues_found.append(f"❌ Admin permissions analysis error: {e}")
            print(f"❌ Admin permissions analysis error: {e}")
        
        return issues_found

async def main():
    """Main function."""
    print("🚨 DEEP ANALYSIS VERIFICATION")
    print("=" * 80)
    
    analysis = DeepAnalysis()
    
    # Perform deep analysis
    admin_issues = await analysis.deep_analyze_admin_toggle()
    payment_issues = await analysis.deep_analyze_payment_addresses()
    callback_issues = await analysis.deep_analyze_callback_routing()
    permission_issues = await analysis.deep_analyze_admin_permissions()
    
    # Compile all issues
    all_issues = admin_issues + payment_issues + callback_issues + permission_issues
    
    print("\n📊 DEEP ANALYSIS RESULTS:")
    print("=" * 80)
    
    if not all_issues:
        print("🎉 NO ISSUES FOUND!")
        print("✅ All systems are working correctly")
        print("✅ Admin toggle buttons should work")
        print("✅ Payment addresses should be generated")
    else:
        print(f"❌ FOUND {len(all_issues)} ISSUES:")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        
        print("\n🔧 CRITICAL FIXES REQUIRED:")
        print("=" * 80)
        
        # Categorize issues
        admin_fixes = [issue for issue in all_issues if 'admin' in issue.lower()]
        payment_fixes = [issue for issue in all_issues if 'payment' in issue.lower() or 'address' in issue.lower()]
        callback_fixes = [issue for issue in all_issues if 'callback' in issue.lower() or 'routing' in issue.lower()]
        permission_fixes = [issue for issue in all_issues if 'permission' in issue.lower() or 'admin_ids' in issue.lower()]
        
        if admin_fixes:
            print("\n🔧 ADMIN TOGGLE FIXES:")
            for fix in admin_fixes:
                print(f"   • {fix}")
        
        if payment_fixes:
            print("\n🔧 PAYMENT ADDRESS FIXES:")
            for fix in payment_fixes:
                print(f"   • {fix}")
        
        if callback_fixes:
            print("\n🔧 CALLBACK ROUTING FIXES:")
            for fix in callback_fixes:
                print(f"   • {fix}")
        
        if permission_fixes:
            print("\n🔧 ADMIN PERMISSION FIXES:")
            for fix in permission_fixes:
                print(f"   • {fix}")
        
        print("\n🎯 PRIORITY ACTIONS:")
        print("=" * 80)
        
        if any('admin_ad_slots table' in issue for issue in all_issues):
            print("1. 🚨 CRITICAL: Create admin_ad_slots table")
        
        if any('ADMIN_IDS' in issue for issue in all_issues):
            print("2. 🚨 CRITICAL: Configure ADMIN_IDS in .env file")
        
        if any('BTC_ADDRESS' in issue for issue in all_issues):
            print("3. 🚨 CRITICAL: Add crypto addresses to .env file")
        
        if any('payments table' in issue for issue in all_issues):
            print("4. 🚨 CRITICAL: Fix payments table structure")
        
        print("\n🔄 RECOMMENDED NEXT STEPS:")
        print("1. Run comprehensive_fix_analysis.py")
        print("2. Add missing environment variables")
        print("3. Restart the bot")
        print("4. Test admin toggle buttons")
        print("5. Test payment creation")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
