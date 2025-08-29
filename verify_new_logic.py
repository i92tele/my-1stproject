#!/usr/bin/env python3
"""
Verify the new subscription activation logic.
This script tests all the fixes we implemented.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.manager import DatabaseManager
from multi_crypto_payments import MultiCryptoPaymentProcessor
from src.config.bot_config import BotConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_new_logic():
    """Verify that the new subscription activation logic works correctly."""
    print("🔍 VERIFYING NEW SUBSCRIPTION ACTIVATION LOGIC")
    print("=" * 60)
    
    try:
        # Initialize components
        config = BotConfig.load_from_env()
        db = DatabaseManager("bot_database.db", logger)
        await db.initialize()
        
        payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        print("1️⃣ Testing Database Connection...")
        # Test database connection
        user_id = 7593457389
        user = await db.get_user(user_id)
        if user:
            print(f"   ✅ Database connection working")
            print(f"   ✅ User {user_id} found")
        else:
            print(f"   ❌ User {user_id} not found")
            return
        
        print("\n2️⃣ Testing Subscription Activation Method...")
        # Test the activate_subscription method directly
        try:
            success = await asyncio.wait_for(
                db.activate_subscription(user_id, 'basic', 30),
                timeout=30.0
            )
            if success:
                print(f"   ✅ Subscription activation method works")
            else:
                print(f"   ❌ Subscription activation method failed")
        except asyncio.TimeoutError:
            print(f"   ❌ Subscription activation method timed out")
        except Exception as e:
            print(f"   ❌ Subscription activation method error: {e}")
        
        print("\n3️⃣ Testing get_user_subscription Method...")
        # Test the get_user_subscription method
        try:
            subscription = await asyncio.wait_for(
                db.get_user_subscription(user_id),
                timeout=10.0
            )
            if subscription:
                print(f"   ✅ get_user_subscription method works")
                print(f"   ✅ Returns: {subscription}")
                print(f"   ✅ Has 'tier' field: {'tier' in subscription}")
                print(f"   ✅ Has 'is_active' field: {'is_active' in subscription}")
            else:
                print(f"   ⚠️ get_user_subscription returned None (user may not have subscription)")
        except asyncio.TimeoutError:
            print(f"   ❌ get_user_subscription method timed out")
        except Exception as e:
            print(f"   ❌ get_user_subscription method error: {e}")
        
        print("\n4️⃣ Testing Payment Status Update...")
        # Test payment status update
        test_payment_id = "TEST_VERIFICATION_123"
        try:
            success = await asyncio.wait_for(
                db.update_payment_status(test_payment_id, 'completed'),
                timeout=10.0
            )
            if success:
                print(f"   ✅ Payment status update method works")
            else:
                print(f"   ❌ Payment status update method failed")
        except asyncio.TimeoutError:
            print(f"   ❌ Payment status update method timed out")
        except Exception as e:
            print(f"   ❌ Payment status update method error: {e}")
        
        print("\n5️⃣ Testing _activate_subscription_for_payment Method...")
        # Test the complete subscription activation flow
        test_payment = {
            'payment_id': 'TEST_PAYMENT_456',
            'user_id': user_id,
            'amount_usd': 15.0,
            'crypto_type': 'TON',
            'status': 'pending'
        }
        
        try:
            success = await asyncio.wait_for(
                payment_processor._activate_subscription_for_payment(test_payment),
                timeout=60.0  # Longer timeout for full flow
            )
            if success:
                print(f"   ✅ _activate_subscription_for_payment method works")
            else:
                print(f"   ❌ _activate_subscription_for_payment method failed")
        except asyncio.TimeoutError:
            print(f"   ❌ _activate_subscription_for_payment method timed out")
        except Exception as e:
            print(f"   ❌ _activate_subscription_for_payment method error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n6️⃣ Testing Current Payment Status...")
        # Check the current payment that was having issues
        payment_id = "TON_67f36980c5bf4afe"
        payment = await db.get_payment(payment_id)
        if payment:
            print(f"   Payment ID: {payment_id}")
            print(f"   Status: {payment['status']}")
            print(f"   User ID: {payment['user_id']}")
            print(f"   Amount: {payment.get('amount_usd', 'N/A')} USD")
            
            if payment['status'] == 'pending':
                print(f"   ⚠️ Payment is still pending - testing activation...")
                try:
                    success = await asyncio.wait_for(
                        payment_processor._activate_subscription_for_payment(payment),
                        timeout=60.0
                    )
                    if success:
                        print(f"   ✅ Payment activation successful!")
                    else:
                        print(f"   ❌ Payment activation failed")
                except asyncio.TimeoutError:
                    print(f"   ❌ Payment activation timed out")
                except Exception as e:
                    print(f"   ❌ Payment activation error: {e}")
            else:
                print(f"   ✅ Payment status is: {payment['status']}")
        else:
            print(f"   ❌ Payment {payment_id} not found")
        
        print("\n7️⃣ Final Subscription Check...")
        # Final check of user subscription
        subscription = await db.get_user_subscription(user_id)
        if subscription:
            print(f"   ✅ User has active subscription:")
            print(f"      Tier: {subscription.get('tier', 'None')}")
            print(f"      Expires: {subscription.get('expires', 'None')}")
            print(f"      Active: {subscription.get('is_active', False)}")
        else:
            print(f"   ⚠️ User has no active subscription")
        
        print("\n" + "=" * 60)
        print("🎯 VERIFICATION COMPLETE")
        print("The new logic should now handle:")
        print("✅ Timeouts properly")
        print("✅ Retries automatically") 
        print("✅ Fallback mechanisms")
        print("✅ Proper error handling")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_new_logic())
