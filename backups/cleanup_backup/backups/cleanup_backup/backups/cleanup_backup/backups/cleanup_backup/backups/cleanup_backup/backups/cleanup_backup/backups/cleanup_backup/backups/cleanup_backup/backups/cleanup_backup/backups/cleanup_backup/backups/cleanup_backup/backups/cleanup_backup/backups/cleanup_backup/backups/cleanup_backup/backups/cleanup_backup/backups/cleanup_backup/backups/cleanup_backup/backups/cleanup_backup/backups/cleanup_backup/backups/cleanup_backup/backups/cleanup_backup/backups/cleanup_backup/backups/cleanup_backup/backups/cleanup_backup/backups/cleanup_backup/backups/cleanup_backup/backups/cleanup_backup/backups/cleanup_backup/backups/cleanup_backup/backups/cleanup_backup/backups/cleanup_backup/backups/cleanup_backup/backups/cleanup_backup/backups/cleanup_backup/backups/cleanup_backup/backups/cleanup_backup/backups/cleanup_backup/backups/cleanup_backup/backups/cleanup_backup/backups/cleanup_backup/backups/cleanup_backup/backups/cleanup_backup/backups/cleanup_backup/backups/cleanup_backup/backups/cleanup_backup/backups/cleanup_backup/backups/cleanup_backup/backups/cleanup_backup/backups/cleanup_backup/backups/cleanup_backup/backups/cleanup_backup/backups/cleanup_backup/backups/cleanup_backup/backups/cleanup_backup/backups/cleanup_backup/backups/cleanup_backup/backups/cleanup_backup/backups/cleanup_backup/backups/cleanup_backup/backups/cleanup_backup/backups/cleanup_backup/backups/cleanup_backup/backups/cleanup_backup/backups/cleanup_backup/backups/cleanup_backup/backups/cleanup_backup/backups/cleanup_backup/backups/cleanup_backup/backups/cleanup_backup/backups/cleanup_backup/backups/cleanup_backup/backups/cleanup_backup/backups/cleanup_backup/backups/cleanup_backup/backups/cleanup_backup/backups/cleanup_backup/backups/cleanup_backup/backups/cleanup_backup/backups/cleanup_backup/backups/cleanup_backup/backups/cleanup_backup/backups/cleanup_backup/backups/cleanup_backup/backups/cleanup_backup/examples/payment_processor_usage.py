#!/usr/bin/env python3
"""
Example usage of PaymentProcessor for TON cryptocurrency payments.
"""

import asyncio
import logging
import os
from datetime import datetime

# Add src to path
import sys
sys.path.append('src')

from payment_processor import PaymentProcessor, initialize_payment_processor
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Example usage of PaymentProcessor."""
    
    # Initialize database
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    # Initialize payment processor
    payment_processor = PaymentProcessor(db_manager, logger)
    await payment_processor.initialize()
    
    try:
        # Example 1: Create a payment request
        user_id = 12345
        tier = 'basic'
        
        payment_request = await payment_processor.create_payment_request(
            user_id=user_id,
            tier=tier,
            amount_usd=15
        )
        
        if payment_request.get('success') is False:
            print(f"❌ Failed to create payment: {payment_request.get('error')}")
            return
        
        print(f"✅ Created payment request:")
        print(f"  Payment ID: {payment_request['payment_id']}")
        print(f"  Amount: {payment_request['amount_ton']} TON (${payment_request['amount_usd']})")
        print(f"  Payment URL: {payment_request['payment_url']}")
        print(f"  Expires: {payment_request['expires_at']}")
        print(f"  Tier: {payment_request['tier']}")
        print(f"  Slots created: {payment_request['slots_created']}")
        
        # Example 2: Check payment status
        payment_id = payment_request['payment_id']
        status = await payment_processor.get_payment_status(payment_id)
        
        print(f"\n📊 Payment Status:")
        print(f"  Status: {status['payment']['status']}")
        print(f"  Is Expired: {status['is_expired']}")
        if status.get('verification'):
            print(f"  Verification: {status['verification']}")
        
        # Example 3: Verify payment (simulated)
        verification = await payment_processor.verify_payment(payment_id)
        print(f"\n🔍 Payment Verification:")
        print(f"  Success: {verification['success']}")
        print(f"  Payment Verified: {verification.get('payment_verified', False)}")
        
        # Example 4: Process successful payment (simulated)
        if verification.get('payment_verified'):
            result = await payment_processor.process_successful_payment(payment_id)
            print(f"\n✅ Payment Processing:")
            print(f"  Success: {result['success']}")
            if result['success']:
                print(f"  User ID: {result['user_id']}")
                print(f"  Tier: {result['tier']}")
                print(f"  Slots: {result['slots']}")
        
        # Example 5: Clean up expired payments
        cleanup_result = await payment_processor.cleanup_expired_payments()
        print(f"\n🧹 Cleanup Result:")
        print(f"  Success: {cleanup_result['success']}")
        print(f"  Cleaned Count: {cleanup_result.get('cleaned_count', 0)}")
        
        # Example 6: Get tier information
        print(f"\n📋 Available Tiers:")
        for tier_name, tier_config in payment_processor.tiers.items():
            print(f"  {tier_name.title()}:")
            print(f"    Slots: {tier_config['slots']}")
            print(f"    Price: ${tier_config['price_usd']}")
            print(f"    Duration: {tier_config['duration_days']} days")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        # Close payment processor
        await payment_processor.close()

async def test_different_tiers():
    """Test creating payments for different tiers."""
    
    db_manager = DatabaseManager('data/bot.db', logger)
    await db_manager.initialize()
    
    payment_processor = PaymentProcessor(db_manager, logger)
    await payment_processor.initialize()
    
    try:
        tiers = ['basic', 'pro', 'enterprise']
        user_id = 12345
        
        for tier in tiers:
            print(f"\n🔄 Testing {tier} tier...")
            
            # Create payment request
            payment_request = await payment_processor.create_payment_request(
                user_id=user_id,
                tier=tier
            )
            
            if payment_request.get('success') is False:
                print(f"❌ Failed to create {tier} payment: {payment_request.get('error')}")
                continue
            
            print(f"✅ {tier.title()} payment created:")
            print(f"  Amount: {payment_request['amount_ton']} TON")
            print(f"  Slots: {payment_request['slots_created']}")
            print(f"  URL: {payment_request['payment_url']}")
            
            # Simulate successful payment
            await payment_processor.process_successful_payment(payment_request['payment_id'])
            
            # Check user subscription
            subscription = await db_manager.get_user_subscription(user_id)
            if subscription:
                print(f"  ✅ Subscription active: {subscription['tier']} until {subscription['expires']}")
            
            # Get user slots
            slots = await db_manager.get_user_slots(user_id)
            print(f"  📊 User has {len(slots)} ad slots")
            
    except Exception as e:
        logger.error(f"Error testing tiers: {e}")
    
    finally:
        await payment_processor.close()

if __name__ == "__main__":
    # Set up environment variables for TON
    os.environ.update({
        'TON_MERCHANT_WALLET': 'EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t',
        'TON_API_KEY': 'your_ton_api_key_here',  # Get from https://toncenter.com/
    })
    
    # Run examples
    asyncio.run(main())
    
    # Uncomment to test different tiers
    # asyncio.run(test_different_tiers()) 