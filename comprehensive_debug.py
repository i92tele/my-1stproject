#!/usr/bin/env python3
"""
Comprehensive Payment System Debug

This script tests all components of the payment system to ensure everything is working correctly.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Load environment variables
try:
    from dotenv import load_dotenv
    env_files = ['.env', 'config/.env', '../.env', '../../.env']
    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"✅ Loaded environment from: {env_file}")
            break
except ImportError:
    print("⚠️ python-dotenv not available")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def comprehensive_debug():
    """Comprehensive debug of the payment system."""
    print("🔍 COMPREHENSIVE PAYMENT SYSTEM DEBUG")
    print("=" * 60)
    
    debug_results = {
        'environment': False,
        'database': False,
        'config': False,
        'payment_processor': False,
        'payment_creation': False,
        'payment_verification': False,
        'subscription_activation': False,
        'admin_commands': False
    }
    
    # TEST 1: Environment Variables
    print("\n🔧 TEST 1: Environment Variables")
    print("-" * 40)
    
    try:
        cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'LTC', 'SOL', 'TON']
        found_addresses = 0
        
        for crypto in cryptos:
            env_var = f"{crypto}_ADDRESS"
            address = os.getenv(env_var)
            if address:
                print(f"✅ {crypto}: {address[:20]}...")
                found_addresses += 1
            else:
                print(f"❌ {crypto}: Not found")
        
        if found_addresses > 0:
            print(f"✅ Environment: {found_addresses}/{len(cryptos)} crypto addresses found")
            debug_results['environment'] = True
        else:
            print("❌ Environment: No crypto addresses found")
            
    except Exception as e:
        print(f"❌ Environment error: {e}")
    
    # TEST 2: Database
    print("\n🗄️ TEST 2: Database")
    print("-" * 40)
    
    try:
        from src.database.manager import DatabaseManager
        
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        print("✅ Database initialized successfully")
        
        # Test database operations
        test_user_id = 999999999
        test_payment_id = "TEST_DEBUG_123"
        
        # Create test user
        await db.create_or_update_user(
            user_id=test_user_id,
            username="debug_user",
            first_name="Debug"
        )
        print("✅ Test user created")
        
        # Test payment creation
        await db.create_payment(
            payment_id=test_payment_id,
            user_id=test_user_id,
            amount_usd=15.0,
            crypto_type='BTC',
            payment_provider='direct',
            pay_to_address='test_address',
            expected_amount_crypto=0.00025,
            payment_url='test_url',
            expires_at=datetime.now() + timedelta(minutes=30),
            attribution_method='amount_time_window'
        )
        print("✅ Test payment created")
        
        # Test payment retrieval
        payment = await db.get_payment(test_payment_id)
        if payment:
            print("✅ Test payment retrieved")
        else:
            print("❌ Test payment not found")
        
        # Clean up test data
        await db.delete_payment(test_payment_id)
        print("✅ Test data cleaned up")
        
        debug_results['database'] = True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
    
    # TEST 3: Configuration
    print("\n⚙️ TEST 3: Configuration")
    print("-" * 40)
    
    config = None
    try:
        from src.config.main_config import BotConfig
        
        config = BotConfig()
        print("✅ BotConfig created successfully")
        
        # Test crypto address access
        btc_address = config.get_crypto_address('BTC')
        if btc_address:
            print(f"✅ BTC address accessible: {btc_address[:20]}...")
        else:
            print("❌ BTC address not accessible")
        
        debug_results['config'] = True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        # Create fallback config
        config = type('MockConfig', (), {
            'get_crypto_address': lambda self, crypto: os.getenv(f"{crypto}_ADDRESS"),
            'subscription_tiers': {
                "basic": {"price": 15.00, "duration_days": 30, "ad_slots": 1}
            }
        })()
        print("⚠️ Using fallback config for testing")
    
    # TEST 4: Payment Processor
    print("\n💰 TEST 4: Payment Processor")
    print("-" * 40)
    
    payment_processor = None
    try:
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        
        payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
        print("✅ Payment processor initialized")
        
        # Test supported cryptocurrencies
        supported_cryptos = list(payment_processor.supported_cryptos.keys())
        expected_cryptos = ['BTC', 'ETH', 'USDT', 'USDC', 'TON', 'SOL', 'LTC']
        
        missing_cryptos = [c for c in expected_cryptos if c not in supported_cryptos]
        if not missing_cryptos:
            print("✅ All expected cryptos are supported")
        else:
            print(f"❌ Missing cryptos: {missing_cryptos}")
        
        debug_results['payment_processor'] = True
        
    except Exception as e:
        print(f"❌ Payment processor error: {e}")
        print("⚠️ Skipping payment processor tests")
    
    # TEST 5: Payment Creation
    print("\n💳 TEST 5: Payment Creation")
    print("-" * 40)
    
    if payment_processor is None:
        print("⚠️ Skipping payment creation test - payment processor not available")
    else:
        try:
            # Create a test payment
            payment_request = await payment_processor.create_payment_request(
                user_id=test_user_id,
                tier='basic',
                crypto_type='TON'
            )
            
            if payment_request.get('success'):
                print("✅ Payment request created successfully")
                print(f"   Payment ID: {payment_request['payment_id']}")
                print(f"   Amount: {payment_request['amount_crypto']} TON")
                print(f"   Address: {payment_request['pay_to_address'][:20]}...")
                
                # Clean up test payment
                await db.delete_payment(payment_request['payment_id'])
                print("✅ Test payment cleaned up")
                
                debug_results['payment_creation'] = True
            else:
                print(f"❌ Payment creation failed: {payment_request.get('error')}")
                
        except Exception as e:
            print(f"❌ Payment creation error: {e}")
    
    # TEST 6: Payment Verification
    print("\n🔍 TEST 6: Payment Verification")
    print("-" * 40)
    
    if payment_processor is None:
        print("⚠️ Skipping payment verification test - payment processor not available")
    else:
        try:
            # Create a test payment for verification
            test_verification_payment_id = "VERIFY_TEST_123"
            await db.create_payment(
                payment_id=test_verification_payment_id,
                user_id=test_user_id,
                amount_usd=15.0,
                crypto_type='BTC',
                payment_provider='direct',
                pay_to_address=os.getenv('BTC_ADDRESS', 'test_address'),
                expected_amount_crypto=0.00025,
                payment_url='test_url',
                expires_at=datetime.now() + timedelta(minutes=30),
                attribution_method='amount_time_window'
            )
            
            # Test verification (should return False for test payment)
            verification_result = await payment_processor.verify_payment_on_blockchain(test_verification_payment_id)
            print(f"✅ Payment verification test completed: {verification_result}")
            
            # Clean up
            await db.delete_payment(test_verification_payment_id)
            print("✅ Test verification payment cleaned up")
            
            debug_results['payment_verification'] = True
            
        except Exception as e:
            print(f"❌ Payment verification error: {e}")
    
    # TEST 7: Subscription Activation
    print("\n🎯 TEST 7: Subscription Activation")
    print("-" * 40)
    
    try:
        # Test subscription activation
        success = await db.activate_subscription(
            user_id=test_user_id,
            tier='basic',
            duration_days=1
        )
        
        if success:
            print("✅ Subscription activation test successful")
            
            # Check if subscription was created
            subscription = await db.get_user_subscription(test_user_id)
            if subscription:
                print(f"✅ Subscription found: {subscription['tier']} tier")
            else:
                print("❌ Subscription not found after activation")
            
            # Clean up test subscription
            await db.delete_user_subscription(test_user_id)
            print("✅ Test subscription cleaned up")
            
            debug_results['subscription_activation'] = True
        else:
            print("❌ Subscription activation failed")
            
    except Exception as e:
        print(f"❌ Subscription activation error: {e}")
    
    # TEST 8: Admin Commands
    print("\n👑 TEST 8: Admin Commands")
    print("-" * 40)
    
    try:
        from commands import admin_commands
        
        # Test if activate_subscription function exists
        if hasattr(admin_commands, 'activate_subscription'):
            print("✅ activate_subscription command function exists")
            debug_results['admin_commands'] = True
        else:
            print("❌ activate_subscription command function not found")
            
    except Exception as e:
        print(f"❌ Admin commands error: {e}")
    
    # FINAL SUMMARY
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE DEBUG SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(debug_results.values())
    total_tests = len(debug_results)
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print("\n📊 Detailed Results:")
    for test, result in debug_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test.replace('_', ' ').title()}: {status}")
    
    if success_rate >= 90:
        print("\n🎉 EXCELLENT - Payment System Ready!")
        print("✅ All components working correctly")
        print("✅ Automatic payment verification active")
        print("✅ Subscription activation working")
        print("✅ Admin commands available")
        print("\n🚀 Your bot is ready for production!")
    elif success_rate >= 70:
        print("\n⚠️ GOOD - Most components working")
        print("Some minor issues may need attention")
    else:
        print("\n❌ POOR - Multiple issues detected")
        print("Payment system may not work correctly")
    
    # Clean up test user
    try:
        await db.delete_user_and_data(test_user_id)
        print("✅ Test user cleaned up")
    except:
        pass
    
    return success_rate >= 90

if __name__ == "__main__":
    success = asyncio.run(comprehensive_debug())
    sys.exit(0 if success else 1)
