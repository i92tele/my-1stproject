#!/usr/bin/env python3
"""
Check BTC Methods
Check what BTC verification methods are available in the payment processor
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function."""
    print("🔍 CHECKING BTC VERIFICATION METHODS")
    print("=" * 50)
    
    try:
        from src.config.main_config import BotConfig
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        from src.database.manager import DatabaseManager
        
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        print("📋 AVAILABLE BTC METHODS:")
        print("-" * 30)
        
        # Check all methods that contain 'btc' or 'bitcoin'
        btc_methods = []
        for method_name in dir(processor):
            if 'btc' in method_name.lower() or 'bitcoin' in method_name.lower():
                btc_methods.append(method_name)
        
        if btc_methods:
            for method in sorted(btc_methods):
                print(f"  ✅ {method}")
        else:
            print("  ❌ No BTC methods found")
        
        print("\n📋 ALL VERIFICATION METHODS:")
        print("-" * 30)
        
        # Check all verification methods
        verify_methods = []
        for method_name in dir(processor):
            if 'verify' in method_name.lower():
                verify_methods.append(method_name)
        
        if verify_methods:
            for method in sorted(verify_methods):
                print(f"  ✅ {method}")
        else:
            print("  ❌ No verification methods found")
        
        print("\n🔧 TESTING BTC VERIFICATION:")
        print("-" * 30)
        
        # Test the actual BTC verification
        try:
            # Get a pending BTC payment
            conn = await db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT payment_id, expected_amount_crypto, pay_to_address, created_at
                FROM payments 
                WHERE crypto_type = 'BTC' AND status = 'pending'
                LIMIT 1
            """)
            
            payment = cursor.fetchone()
            
            if payment:
                payment_id, expected_amount, address, created_at = payment
                print(f"📋 Testing payment: {payment_id}")
                print(f"💰 Expected: {expected_amount} BTC")
                print(f"🎯 Address: {address}")
                
                # Try to verify the payment
                try:
                    result = await processor.verify_payment(payment_id)
                    print(f"✅ Verification result: {result}")
                except Exception as e:
                    print(f"❌ Verification error: {e}")
                    
                    # Check if it's a method not found error
                    if "has no attribute" in str(e):
                        print("💡 The verification method doesn't exist")
                    elif "API" in str(e):
                        print("💡 API error - check API key or rate limits")
                    else:
                        print("💡 Unknown error during verification")
            else:
                print("❌ No pending BTC payments found")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Error testing verification: {e}")
        
        print("\n💡 TROUBLESHOOTING:")
        print("-" * 30)
        print("1. Check if the BTC verification method exists")
        print("2. Verify the API key is working")
        print("3. Check if the payment amount matches exactly")
        print("4. Verify the payment is within the time window")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
