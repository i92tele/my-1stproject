#!/usr/bin/env python3
"""
BTC Payment Verification Check
Check why BTC payment wasn't verified
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BTCPaymentChecker:
    """Check BTC payment verification issues."""
    
    def __init__(self):
        self.logger = logger
    
    async def check_btc_payment_verification(self):
        """Check BTC payment verification process."""
        print("💰 BTC PAYMENT VERIFICATION CHECK")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Get pending BTC payments
            pending_payments = await db.get_pending_payments(age_limit_minutes=1440)  # 24 hours
            btc_payments = [p for p in pending_payments if p.get('crypto_type') == 'BTC']
            
            print(f"📊 Found {len(btc_payments)} pending BTC payments")
            
            for payment in btc_payments:
                payment_id = payment['payment_id']
                print(f"\n🔍 Checking payment: {payment_id}")
                print(f"   Amount: {payment.get('expected_amount_crypto')} BTC")
                print(f"   Address: {payment.get('pay_to_address')}")
                print(f"   Created: {payment.get('created_at')}")
                print(f"   Status: {payment.get('status')}")
                
                # Test verification
                print(f"\n🧪 Testing verification for {payment_id}...")
                
                try:
                    # Test BTC verification directly
                    btc_address = payment.get('pay_to_address')
                    required_amount = float(payment.get('expected_amount_crypto', 0))
                    
                    if btc_address and required_amount > 0:
                        # Test verification with different APIs
                        await self.test_btc_apis(btc_address, required_amount, payment_id)
                    else:
                        print("❌ Missing BTC address or amount")
                        
                except Exception as e:
                    print(f"❌ Error testing BTC verification: {e}")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error checking BTC payments: {e}")
    
    async def test_btc_apis(self, btc_address: str, required_amount: float, payment_id: str):
        """Test different BTC APIs for verification."""
        print(f"🔧 Testing BTC APIs for {payment_id}")
        
        # Test 1: BlockCypher API
        print("\n1️⃣ Testing BlockCypher API...")
        try:
            import aiohttp
            
            url = f"https://api.blockcypher.com/v1/btc/main/addrs/{btc_address}/full"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for incoming transactions
                        incoming_txs = [tx for tx in data.get('txs', []) if tx.get('outputs')]
                        
                        print(f"   ✅ BlockCypher API working")
                        print(f"   📊 Found {len(incoming_txs)} transactions")
                        
                        # Check for matching amount
                        for tx in incoming_txs[:5]:  # Check first 5 transactions
                            for output in tx.get('outputs', []):
                                if output.get('addresses', [{}])[0] == btc_address:
                                    amount_btc = output.get('value', 0) / 100000000  # Convert satoshis to BTC
                                    print(f"   💰 Transaction: {amount_btc} BTC")
                                    
                                    # Check if amount matches (with tolerance)
                                    tolerance = 0.03  # 3%
                                    min_required = required_amount * (1.0 - tolerance)
                                    max_allowed = required_amount * (1.0 + tolerance)
                                    
                                    if min_required <= amount_btc <= max_allowed:
                                        print(f"   ✅ Amount matches! Expected: {required_amount}, Found: {amount_btc}")
                                    else:
                                        print(f"   ❌ Amount doesn't match. Expected: {required_amount}, Found: {amount_btc}")
                    else:
                        print(f"   ❌ BlockCypher API error: {response.status}")
                        
        except Exception as e:
            print(f"   ❌ BlockCypher API failed: {e}")
        
        # Test 2: Blockchain.info API
        print("\n2️⃣ Testing Blockchain.info API...")
        try:
            import aiohttp
            
            url = f"https://blockchain.info/rawaddr/{btc_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        txs = data.get('txs', [])
                        print(f"   ✅ Blockchain.info API working")
                        print(f"   📊 Found {len(txs)} transactions")
                        
                        # Check for matching amount
                        for tx in txs[:5]:  # Check first 5 transactions
                            for output in tx.get('out', []):
                                if output.get('addr') == btc_address:
                                    amount_btc = output.get('value', 0) / 100000000  # Convert satoshis to BTC
                                    print(f"   💰 Transaction: {amount_btc} BTC")
                    else:
                        print(f"   ❌ Blockchain.info API error: {response.status}")
                        
        except Exception as e:
            print(f"   ❌ Blockchain.info API failed: {e}")
        
        # Test 3: Manual verification
        print("\n3️⃣ Manual verification check...")
        try:
            # Check if payment is within time window
            payment_time = datetime.fromisoformat(payment_id.split('_')[1] if '_' in payment_id else datetime.now().isoformat())
            time_window_start = payment_time - timedelta(minutes=30)
            time_window_end = payment_time + timedelta(minutes=30)
            
            print(f"   ⏰ Time window: {time_window_start} to {time_window_end}")
            print(f"   📍 Current time: {datetime.now()}")
            
            if datetime.now() < time_window_end:
                print(f"   ✅ Payment within time window")
            else:
                print(f"   ❌ Payment outside time window")
                
        except Exception as e:
            print(f"   ❌ Manual verification failed: {e}")
    
    async def check_payment_processor_methods(self):
        """Check if payment processor methods are working."""
        print("\n🔧 PAYMENT PROCESSOR METHODS CHECK")
        print("=" * 50)
        
        try:
            from src.config.main_config import BotConfig
            from src.database.manager import DatabaseManager
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            
            config = BotConfig.load_from_env()
            db = DatabaseManager(config.database_url or "bot_database.db", logger)
            await db.initialize()
            
            processor = MultiCryptoPaymentProcessor(config, db, logger)
            
            # Check if BTC verification method exists
            if hasattr(processor, '_verify_btc_payment'):
                print("✅ BTC verification method exists")
                
                # Test the method signature
                import inspect
                sig = inspect.signature(processor._verify_btc_payment)
                print(f"   Method signature: {sig}")
            else:
                print("❌ BTC verification method not found")
            
            # Check if get_payment_status method exists
            if hasattr(processor, 'get_payment_status'):
                print("✅ get_payment_status method exists")
            else:
                print("❌ get_payment_status method not found")
            
            # Check if verify_payment_on_blockchain method exists
            if hasattr(processor, 'verify_payment_on_blockchain'):
                print("✅ verify_payment_on_blockchain method exists")
            else:
                print("❌ verify_payment_on_blockchain method not found")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error checking payment processor methods: {e}")

async def main():
    """Main function."""
    checker = BTCPaymentChecker()
    
    # Check BTC payment verification
    await checker.check_btc_payment_verification()
    
    # Check payment processor methods
    await checker.check_payment_processor_methods()
    
    print("\n📊 BTC PAYMENT VERIFICATION SUMMARY")
    print("=" * 50)
    print("If BTC payment wasn't verified, possible reasons:")
    print("1. ❌ Payment amount doesn't match expected amount")
    print("2. ❌ Payment sent to wrong address")
    print("3. ❌ Payment outside time window (30 minutes)")
    print("4. ❌ APIs are down or rate limited")
    print("5. ❌ Insufficient confirmations")
    print("6. ❌ Payment verification method has bugs")
    print("\n💡 Check the detailed output above for specific issues")

if __name__ == "__main__":
    asyncio.run(main())

