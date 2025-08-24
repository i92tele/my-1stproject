from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
#!/usr/bin/env python3
"""Create a test payment to match existing TON transaction."""

import sys
import os
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('config/.env')

from config import BotConfig
from src.database.manager import DatabaseManager
from ton_payments import TONPaymentProcessor
import logging

async def create_test_payment():
    """Create a test payment matching existing transaction."""
    print("💰 Creating Test Payment...")
    
    config = BotConfig.load_from_env()
    logger = logging.getLogger(__name__)
    db = DatabaseManager(config, logger)
    
    try:
        await db.initialize()
        
        user_id = 7172873873  # Your admin user ID
        
        # Create a payment that matches the existing transaction
        payment_processor = TONPaymentProcessor(config, db, logger)
        
        # Create payment with the exact amount and memo from your transaction
        from datetime import datetime, timedelta
        
        payment_data = {
            'payment_id': 'TON_EkV9',  # This matches the memo in your transaction
            'user_id': user_id,
            'tier': 'basic',
            'cryptocurrency': 'ton',
            'amount_usd': 9.99,
            'amount_crypto': 2.83,  # This matches your transaction
            'wallet_address': config.ton_address,
            'payment_memo': 'PAY-TON_EkV9',  # This matches your transaction
            'status': 'pending',
            'created_at': datetime.now() - timedelta(hours=2),
            'expires_at': datetime.now() + timedelta(hours=2)
        }
        
        print(f"📋 Creating payment: {payment_data['payment_id']}")
        print(f"   Amount: {payment_data['amount_crypto']} TON")
        print(f"   Memo: {payment_data['payment_memo']}")
        
        # Insert payment into database
        async with db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO payments (
                    payment_id, user_id, tier, cryptocurrency, amount_usd, 
                    amount_crypto, wallet_address, payment_memo, status, 
                    created_at, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''', 
            payment_data['payment_id'], payment_data['user_id'], payment_data['tier'],
            payment_data['cryptocurrency'], payment_data['amount_usd'], 
            payment_data['amount_crypto'], payment_data['wallet_address'],
            payment_data['payment_memo'], payment_data['status'],
            payment_data['created_at'], payment_data['expires_at']
            )
        
        print("✅ Test payment created!")
        
        # Now test verification
        print(f"\n🔍 Testing payment verification...")
        is_verified = await payment_processor.verify_payment_on_blockchain(payment_data)
        print(f"   Verified: {'✅ Yes' if is_verified else '❌ No'}")
        
        if is_verified:
            print("🎉 Payment detected! Activating subscription...")
            await db.activate_subscription(user_id, 'basic', 30)
            await db.update_payment_status(payment_data['payment_id'], 'completed')
            print("✅ Subscription activated!")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await db.close()

if __name__ == "__main__":
    asyncio.run(create_test_payment()) 