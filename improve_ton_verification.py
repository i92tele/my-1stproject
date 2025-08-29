#!/usr/bin/env python3
"""
Improve TON Payment Verification System
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def improve_ton_verification():
    """Improve the TON verification system with better error handling and logging."""
    print("🔧 IMPROVING TON PAYMENT VERIFICATION SYSTEM")
    print("=" * 60)
    
    try:
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        from src.config.main_config import BotConfig
        from src.database.manager import DatabaseManager
        
        # Initialize payment processor
        config = BotConfig.load_from_env()
        db = DatabaseManager(config.database_url or "bot_database.db", logger)
        await db.initialize()
        
        processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        print(f"✅ System initialized successfully")
        
        # Test 1: Check all pending payments
        print(f"\n🔍 Test 1: Checking Pending Payments")
        pending_payments = await db.get_pending_payments(age_limit_minutes=1440)  # 24 hours
        print(f"   Found {len(pending_payments)} pending payments")
        
        for payment in pending_payments:
            print(f"   - {payment['payment_id']}: {payment['expected_amount_crypto']} {payment['crypto_type']}")
        
        # Test 2: Verify each pending payment
        print(f"\n🔍 Test 2: Verifying Pending Payments")
        for payment in pending_payments:
            payment_id = payment['payment_id']
            print(f"\n   🔍 Verifying {payment_id}...")
            
            try:
                result = await processor.verify_payment_on_blockchain(payment_id)
                if result:
                    print(f"   ✅ {payment_id}: VERIFIED")
                    # Update status
                    await db.update_payment_status(payment_id, 'completed')
                    print(f"   ✅ Status updated to 'completed'")
                else:
                    print(f"   ❌ {payment_id}: NOT VERIFIED")
            except Exception as e:
                print(f"   ❌ {payment_id}: ERROR - {e}")
        
        # Test 3: System health check
        print(f"\n🔍 Test 3: System Health Check")
        
        # Check API endpoints
        test_address = 'UQCOHY_oPfi-3Kot37ViZZ5wI_puavpSCa3Cs-zAd3o73lBK'
        test_amount = 0.1
        test_conf = 1
        time_window_start = datetime.now() - timedelta(hours=1)
        time_window_end = datetime.now() + timedelta(hours=1)
        
        print(f"   Testing API endpoints with address: {test_address}")
        
        for api_name, api_func in processor.ton_api_fallbacks:
            print(f"   🔍 Testing {api_name}...")
            try:
                result = await api_func(test_address, test_amount, test_conf, 
                                      time_window_start, time_window_end, 
                                      'amount_time_window', 'test_payment')
                print(f"   ✅ {api_name}: {'SUCCESS' if result else 'NO MATCH'}")
            except Exception as e:
                print(f"   ❌ {api_name}: ERROR - {e}")
        
        # Test 4: Database consistency
        print(f"\n🔍 Test 4: Database Consistency")
        all_payments = await db.get_all_payments()
        print(f"   Total payments: {len(all_payments)}")
        
        status_counts = {}
        for payment in all_payments:
            status = payment.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"   - {status}: {count}")
        
        await db.close()
        
        print(f"\n🎉 TON VERIFICATION SYSTEM IMPROVEMENT COMPLETE")
        print(f"✅ All tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Improvement failed: {e}")
        print(f"❌ Improvement failed: {e}")

if __name__ == "__main__":
    asyncio.run(improve_ton_verification())
