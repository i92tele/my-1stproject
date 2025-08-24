from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
#!/usr/bin/env python3
"""
Payment Diagnostic Script
Checks payment processing and subscription activation
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from src.database.manager import DatabaseManager
from ton_payments import TONPaymentProcessor

load_dotenv('config/.env')

async def diagnose_payment_issues():
    """Diagnose payment processing issues."""
    print("🔍 Payment System Diagnostic")
    print("=" * 50)
    
    # Initialize components
    config = BotConfig.load_from_env()
    db = DatabaseManager(config, None)
    payment_processor = TONPaymentProcessor(config, db, None)
    
    await db.initialize()
    
    try:
        # 1. Check recent payments
        print("\n📊 Recent Payments:")
        print("-" * 30)
        
        async with db.pool.acquire() as conn:
            payments = await conn.fetch('''
                SELECT payment_id, user_id, tier, amount_crypto, status, created_at, completed_at
                FROM payments 
                ORDER BY created_at DESC 
                LIMIT 10
            ''')
        
        for payment in payments:
            print(f"Payment ID: {payment['payment_id']}")
            print(f"User ID: {payment['user_id']}")
            print(f"Tier: {payment['tier']}")
            print(f"Amount: {payment['amount_crypto']} TON")
            print(f"Status: {payment['status']}")
            print(f"Created: {payment['created_at']}")
            if payment['completed_at']:
                print(f"Completed: {payment['completed_at']}")
            print("-" * 20)
        
        # 2. Check pending payments
        print("\n⏳ Pending Payments:")
        print("-" * 30)
        
        async with db.pool.acquire() as conn:
            pending = await conn.fetch('''
                SELECT payment_id, user_id, tier, amount_crypto, payment_memo, created_at
                FROM payments 
                WHERE status = 'pending'
                ORDER BY created_at DESC
            ''')
        
        for payment in pending:
            print(f"Payment ID: {payment['payment_id']}")
            print(f"User ID: {payment['user_id']}")
            print(f"Memo: {payment['payment_memo']}")
            print(f"Amount: {payment['amount_crypto']} TON")
            print(f"Created: {payment['created_at']}")
            print("-" * 20)
        
        # 3. Check user subscriptions
        print("\n👤 User Subscriptions:")
        print("-" * 30)
        
        async with db.pool.acquire() as conn:
            users = await conn.fetch('''
                SELECT user_id, subscription_tier, subscription_expires, created_at
                FROM users 
                WHERE subscription_tier IS NOT NULL
                ORDER BY subscription_expires DESC
            ''')
        
        for user in users:
            print(f"User ID: {user['user_id']}")
            print(f"Tier: {user['subscription_tier']}")
            print(f"Expires: {user['subscription_expires']}")
            print(f"Created: {user['created_at']}")
            print("-" * 20)
        
        # 4. Check ad slots
        print("\n📢 Ad Slots:")
        print("-" * 30)
        
        async with db.pool.acquire() as conn:
            slots = await conn.fetch('''
                SELECT user_id, slot_number, is_active, created_at
                FROM ad_slots 
                ORDER BY user_id, slot_number
            ''')
        
        for slot in slots:
            print(f"User ID: {slot['user_id']}")
            print(f"Slot: {slot['slot_number']}")
            print(f"Active: {slot['is_active']}")
            print(f"Created: {slot['created_at']}")
            print("-" * 20)
        
        # 5. Test payment verification
        print("\n🔍 Testing Payment Verification:")
        print("-" * 30)
        
        if pending:
            test_payment = dict(pending[0])
            print(f"Testing verification for payment: {test_payment['payment_id']}")
            
            # Check wallet transactions
            transactions = await payment_processor.get_wallet_transactions(config.ton_address)
            print(f"Found {len(transactions)} recent transactions")
            
            for tx in transactions[:5]:  # Show first 5
                print(f"Amount: {tx.get('amount', 0)} nanoTON")
                print(f"Comment: {tx.get('comment', 'No comment')}")
                print("-" * 10)
            
            # Test verification
            is_verified = await payment_processor.verify_payment_on_blockchain(test_payment)
            print(f"Payment verified: {is_verified}")
        
        # 6. Check payment monitor status
        print("\n📡 Payment Monitor Status:")
        print("-" * 30)
        
        try:
            import psutil
            payment_monitor_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'payment_monitor' in str(proc.info['cmdline']):
                    payment_monitor_running = True
                    print(f"✅ Payment monitor running (PID: {proc.info['pid']})")
                    break
            
            if not payment_monitor_running:
                print("❌ Payment monitor not running")
        except ImportError:
            print("⚠️ psutil not available, cannot check payment monitor")
        
        # 7. Recommendations
        print("\n💡 Recommendations:")
        print("-" * 30)
        
        if pending:
            print("1. Check if payment monitor is running")
            print("2. Verify TON wallet address is correct")
            print("3. Check if payment memo matches")
            print("4. Verify transaction amount")
            print("5. Check blockchain API connectivity")
        else:
            print("1. No pending payments found")
            print("2. Check if payment was created correctly")
            print("3. Verify user subscription status")
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
    
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(diagnose_payment_issues()) 