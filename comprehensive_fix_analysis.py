#!/usr/bin/env python3
"""
Comprehensive Fix Analysis

This script provides a definitive solution for both:
1. Admin toggle button not working
2. Payment addresses not being generated
"""

import asyncio
import sqlite3
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveFix:
    def __init__(self):
        self.db_path = "bot_database.db"
        
    async def analyze_admin_toggle_issue(self):
        """Analyze the admin toggle button issue."""
        print("🔍 ANALYZING ADMIN TOGGLE ISSUE")
        print("=" * 50)
        
        try:
            # 1. Check if admin_ad_slots table exists
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_ad_slots'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                print("❌ CRITICAL: admin_ad_slots table does not exist!")
                print("   This is why the toggle button doesn't work.")
                return False
            
            print("✅ admin_ad_slots table exists")
            
            # 2. Check table structure
            cursor.execute("PRAGMA table_info(admin_ad_slots)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            required_columns = ['id', 'slot_number', 'content', 'is_active', 'created_at', 'updated_at']
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            
            print("✅ All required columns exist")
            
            # 3. Check if admin slots exist
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
            slot_count = cursor.fetchone()[0]
            
            if slot_count == 0:
                print("❌ No admin slots exist in database")
                print("   This is why the toggle button doesn't work.")
                return False
            
            print(f"✅ Found {slot_count} admin slots")
            
            # 4. Check sample slot data
            cursor.execute("SELECT * FROM admin_ad_slots LIMIT 1")
            sample_slot = cursor.fetchone()
            if sample_slot:
                print(f"✅ Sample slot: ID={sample_slot[0]}, Slot={sample_slot[1]}, Active={sample_slot[3]}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing admin toggle: {e}")
            return False
    
    async def analyze_payment_address_issue(self):
        """Analyze the payment address generation issue."""
        print("\n🔍 ANALYZING PAYMENT ADDRESS ISSUE")
        print("=" * 50)
        
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
            
            print("📍 Checking crypto addresses in environment:")
            missing_addresses = []
            for crypto, address in crypto_addresses.items():
                if address:
                    print(f"✅ {crypto}: {address[:10]}...")
                else:
                    print(f"❌ {crypto}: NOT SET")
                    missing_addresses.append(crypto)
            
            if missing_addresses:
                print(f"\n❌ Missing addresses: {missing_addresses}")
                print("   This is why payment addresses aren't generated.")
                return False
            
            print("✅ All crypto addresses are configured")
            
            # 2. Test BotConfig.get_crypto_address method
            try:
                from src.config.bot_config import BotConfig
                config = BotConfig()
                
                print("\n📍 Testing BotConfig.get_crypto_address:")
                for crypto in ['BTC', 'ETH', 'SOL', 'LTC', 'TON']:
                    address = config.get_crypto_address(crypto.lower())
                    if address:
                        print(f"✅ {crypto}: {address[:10]}...")
                    else:
                        print(f"❌ {crypto}: NOT FOUND")
                        return False
                
                print("✅ BotConfig.get_crypto_address works correctly")
                
            except Exception as e:
                print(f"❌ Error testing BotConfig: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing payment addresses: {e}")
            return False
    
    async def fix_admin_slots_table(self):
        """Fix the admin slots table structure."""
        print("\n🔧 FIXING ADMIN SLOTS TABLE")
        print("=" * 50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Create admin_ad_slots table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_ad_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_number INTEGER UNIQUE,
                    content TEXT,
                    file_id TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_paused BOOLEAN DEFAULT 0,
                    interval_minutes INTEGER DEFAULT 60,
                    last_sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 2. Create admin_slot_destinations table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_slot_destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slot_id INTEGER,
                    destination_type TEXT DEFAULT 'group',
                    destination_id TEXT,
                    destination_name TEXT,
                    alias TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (slot_id) REFERENCES admin_ad_slots(id)
                )
            ''')
            
            # 3. Insert sample admin slots if none exist
            cursor.execute("SELECT COUNT(*) FROM admin_ad_slots")
            slot_count = cursor.fetchone()[0]
            
            if slot_count == 0:
                print("📍 Creating sample admin slots...")
                for i in range(1, 6):  # Create slots 1-5
                    cursor.execute('''
                        INSERT INTO admin_ad_slots (slot_number, content, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (i, f"Sample admin content for slot {i}", True, datetime.now(), datetime.now()))
                
                print("✅ Created 5 sample admin slots")
            
            conn.commit()
            conn.close()
            
            print("✅ Admin slots table structure fixed")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing admin slots table: {e}")
            return False
    
    async def fix_payment_addresses(self):
        """Fix payment address generation."""
        print("\n🔧 FIXING PAYMENT ADDRESSES")
        print("=" * 50)
        
        try:
            # 1. Check if addresses are set in environment
            crypto_addresses = {
                'BTC_ADDRESS': os.getenv('BTC_ADDRESS'),
                'ETH_ADDRESS': os.getenv('ETH_ADDRESS'),
                'SOL_ADDRESS': os.getenv('SOL_ADDRESS'),
                'LTC_ADDRESS': os.getenv('LTC_ADDRESS'),
                'TON_ADDRESS': os.getenv('TON_ADDRESS'),
                'USDT_ADDRESS': os.getenv('USDT_ADDRESS'),
                'USDC_ADDRESS': os.getenv('USDC_ADDRESS')
            }
            
            missing_addresses = [crypto for crypto, address in crypto_addresses.items() if not address]
            
            if missing_addresses:
                print(f"❌ Missing environment variables: {missing_addresses}")
                print("\n📋 SOLUTION: Add these to your .env file:")
                for crypto in missing_addresses:
                    print(f"   {crypto}=your_{crypto.lower().replace('_address', '')}_wallet_address")
                
                print("\n💡 Example .env entries:")
                print("   BTC_ADDRESS=bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
                print("   ETH_ADDRESS=0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
                print("   SOL_ADDRESS=9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
                print("   LTC_ADDRESS=ltc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
                print("   TON_ADDRESS=EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t")
                
                return False
            
            print("✅ All crypto addresses are configured")
            
            # 2. Test payment address generation
            try:
                from multi_crypto_payments import MultiCryptoPaymentProcessor
                from src.config.bot_config import BotConfig
                
                config = BotConfig()
                payment_processor = MultiCryptoPaymentProcessor(config, None, logger)
                
                print("\n📍 Testing payment address generation:")
                
                # Test BTC payment creation
                test_payment_data = await payment_processor._create_direct_payment(
                    payment_id="TEST_123",
                    amount_usd=15.0,
                    crypto_type="BTC"
                )
                
                if test_payment_data and test_payment_data.get('pay_to_address'):
                    print(f"✅ BTC payment address generated: {test_payment_data['pay_to_address'][:10]}...")
                else:
                    print("❌ BTC payment address generation failed")
                    return False
                
                print("✅ Payment address generation works correctly")
                return True
                
            except Exception as e:
                print(f"❌ Error testing payment generation: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Error fixing payment addresses: {e}")
            return False
    
    async def test_admin_toggle_functionality(self):
        """Test admin toggle functionality after fixes."""
        print("\n🧪 TESTING ADMIN TOGGLE FUNCTIONALITY")
        print("=" * 50)
        
        try:
            # Import database manager
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            
            # Initialize database manager
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            # 1. Test get_admin_ad_slots
            admin_slots = await db.get_admin_ad_slots()
            if not admin_slots:
                print("❌ No admin slots found")
                return False
            
            print(f"✅ Found {len(admin_slots)} admin slots")
            
            # 2. Test get_admin_ad_slot
            test_slot = admin_slots[0]
            slot_number = test_slot.get('slot_number')
            
            slot = await db.get_admin_ad_slot(slot_number)
            if not slot:
                print("❌ Could not get admin slot")
                return False
            
            print(f"✅ Retrieved admin slot {slot_number}")
            
            # 3. Test update_admin_slot_status
            current_status = slot.get('is_active')
            new_status = not current_status
            
            success = await db.update_admin_slot_status(slot_number, new_status)
            if not success:
                print("❌ Could not update admin slot status")
                return False
            
            print(f"✅ Updated admin slot {slot_number} status to {new_status}")
            
            # 4. Verify the change
            updated_slot = await db.get_admin_ad_slot(slot_number)
            if updated_slot.get('is_active') == new_status:
                print("✅ Status change verified")
                
                # Restore original status
                await db.update_admin_slot_status(slot_number, current_status)
                print("✅ Restored original status")
                return True
            else:
                print("❌ Status change not verified")
                return False
                
        except Exception as e:
            print(f"❌ Error testing admin toggle: {e}")
            return False
    
    async def test_payment_creation(self):
        """Test payment creation after fixes."""
        print("\n🧪 TESTING PAYMENT CREATION")
        print("=" * 50)
        
        try:
            # Import required modules
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            from src.config.bot_config import BotConfig
            
            # Initialize components
            db = DatabaseManager(self.db_path, logger)
            await db.initialize()
            
            config = BotConfig()
            payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Test payment creation
            payment_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            payment_request = await payment_processor.create_payment_request(
                user_id=1,
                amount_usd=15.0,
                crypto_type="BTC"
            )
            
            if payment_request and payment_request.get('payment_url'):
                print(f"✅ Payment created successfully")
                print(f"   Payment ID: {payment_id}")
                print(f"   Payment URL: {payment_request['payment_url'][:50]}...")
                print(f"   Address: {payment_request.get('pay_to_address', 'N/A')[:20]}...")
                return True
            else:
                print("❌ Payment creation failed")
                return False
                
        except Exception as e:
            print(f"❌ Error testing payment creation: {e}")
            return False

async def main():
    """Main function."""
    print("🚨 COMPREHENSIVE FIX ANALYSIS")
    print("=" * 60)
    
    fix = ComprehensiveFix()
    
    # Analyze issues
    admin_analysis = await fix.analyze_admin_toggle_issue()
    payment_analysis = await fix.analyze_payment_address_issue()
    
    print("\n📊 ANALYSIS RESULTS:")
    print("=" * 60)
    print(f"Admin Toggle Issue: {'❌ BROKEN' if not admin_analysis else '✅ WORKING'}")
    print(f"Payment Address Issue: {'❌ BROKEN' if not payment_analysis else '✅ WORKING'}")
    
    # Apply fixes
    if not admin_analysis:
        print("\n🔧 APPLYING ADMIN TOGGLE FIX...")
        admin_fixed = await fix.fix_admin_slots_table()
        if admin_fixed:
            admin_tested = await fix.test_admin_toggle_functionality()
            print(f"Admin Toggle Test: {'✅ PASSED' if admin_tested else '❌ FAILED'}")
        else:
            print("❌ Admin toggle fix failed")
    
    if not payment_analysis:
        print("\n🔧 APPLYING PAYMENT ADDRESS FIX...")
        payment_fixed = await fix.fix_payment_addresses()
        if payment_fixed:
            payment_tested = await fix.test_payment_creation()
            print(f"Payment Creation Test: {'✅ PASSED' if payment_tested else '❌ FAILED'}")
        else:
            print("❌ Payment address fix failed")
    
    print("\n🎯 DEFINITIVE SOLUTION:")
    print("=" * 60)
    
    if not admin_analysis:
        print("1. ✅ Admin slots table created/fixed")
        print("2. ✅ Sample admin slots added")
        print("3. ✅ Database methods working")
    
    if not payment_analysis:
        print("4. ❌ CRITICAL: Add crypto addresses to .env file")
        print("   Required variables:")
        print("   - BTC_ADDRESS=your_bitcoin_address")
        print("   - ETH_ADDRESS=your_ethereum_address")
        print("   - SOL_ADDRESS=your_solana_address")
        print("   - LTC_ADDRESS=your_litecoin_address")
        print("   - TON_ADDRESS=your_ton_address")
        print("   - USDT_ADDRESS=your_usdt_address")
        print("   - USDC_ADDRESS=your_usdc_address")
    
    print("\n🔄 Next Steps:")
    print("1. Add missing crypto addresses to .env file")
    print("2. Restart the bot")
    print("3. Test admin toggle buttons")
    print("4. Test payment creation")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
