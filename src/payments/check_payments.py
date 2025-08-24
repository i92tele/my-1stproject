from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
#!/usr/bin/env python3
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from src.database.manager import DatabaseManager
from ton_payments import TONPaymentProcessor

# Load environment variables
load_dotenv('config/.env')

async def check_payments():
    """Check pending payments and test TON verification."""
    import logging
    logger = logging.getLogger(__name__)
    
    config = BotConfig.load_from_env()
    db = DatabaseManager(config, logger)
    payment_processor = TONPaymentProcessor(config, db, logger)
    
    await db.initialize()
    
    print("🔍 Checking pending payments...")
    
    # Check pending payments
    async with db.pool.acquire() as conn:
        pending_payments = await conn.fetch('''
            SELECT payment_id, user_id, tier, amount_crypto, payment_memo, created_at, status
            FROM payments 
            WHERE cryptocurrency = 'ton'
            ORDER BY created_at DESC
            LIMIT 10
        ''')
    
    print(f"Found {len(pending_payments)} payments:")
    for payment in pending_payments:
        print(f"  - Payment ID: {payment['payment_id']}")
        print(f"    User ID: {payment['user_id']}")
        print(f"    Tier: {payment['tier']}")
        print(f"    Amount: {payment['amount_crypto']} TON")
        print(f"    Status: {payment['status']}")
        print(f"    Memo: {payment['payment_memo']}")
        print(f"    Created: {payment['created_at']}")
        print()
    
    # Test TON wallet transactions
    print("🔍 Testing TON wallet transactions...")
    try:
        transactions = await payment_processor.get_wallet_transactions(config.ton_address)
        print(f"Found {len(transactions)} recent transactions")
        for tx in transactions[:5]:  # Show first 5
            print(f"  - Amount: {tx.get('amount', 'N/A')} nanoTON")
            print(f"    Comment: {tx.get('comment', 'N/A')}")
            print(f"    Time: {tx.get('time', 'N/A')}")
            print()
    except Exception as e:
        print(f"Error getting transactions: {e}")

if __name__ == "__main__":
    asyncio.run(check_payments()) 