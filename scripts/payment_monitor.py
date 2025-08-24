#!/usr/bin/env python3
"""
Payment Monitor (SQLite + MultiCryptoPaymentProcessor)
- Polls pending payments and verifies on-chain (starting with TON)
- Uses database.py async APIs (no raw SQL)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import BotConfig
from src.database.manager import DatabaseManager
from multi_crypto_payments import MultiCryptoPaymentProcessor

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/payment_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv('config/.env')

class PaymentMonitorService:
    def __init__(self):
        self.config = BotConfig.load_from_env() if hasattr(BotConfig, 'load_from_env') else {}
        self.db = DatabaseManager(self.config, logger)
        self.processor = MultiCryptoPaymentProcessor(self.config, self.db, logger)

    async def initialize(self):
        await self.db.initialize()
        logger.info("Payment monitor service initialized (SQLite)")

    async def run(self):
        logger.info("🔍 Starting payment monitoring service (multi-crypto, direct-ready)...")
        await self.initialize()
        try:
            while True:
                try:
                    # Fetch pending payments (not expired)
                    pending = await self.db.get_pending_payments(age_limit_minutes=0)
                    to_check = [p for p in pending if p.get('expires_at') is None or datetime.fromisoformat(p['expires_at']) > datetime.now()]

                    if to_check:
                        logger.info(f"Checking {len(to_check)} pending payments…")
                    for payment in to_check:
                        ok = await self.processor.verify_payment_on_blockchain(payment['payment_id'])
                        if ok:
                            # Subscription activation handled inside processor
                            logger.info(f"✅ Payment completed: {payment['payment_id']}")

                    await asyncio.sleep(30)
                except Exception as cycle_err:
                    logger.error(f"Monitor cycle error: {cycle_err}")
                    await asyncio.sleep(60)
        finally:
            try:
                await self.db.close()
            except Exception:
                pass

async def main():
    monitor = PaymentMonitorService()
    await monitor.run()

if __name__ == '__main__':
    asyncio.run(main())