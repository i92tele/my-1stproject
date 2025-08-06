#!/usr/bin/env python3
import asyncio
import logging
from config import BotConfig
from database import DatabaseManager
from multi_crypto_payments import MultiCryptoPaymentProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Start the payment monitoring service."""
    try:
        # Load configuration
        config = BotConfig.load_from_env()
        db = DatabaseManager(config, logger)
        
        # Initialize database connection
        await db.initialize()
        
        # Create payment processor
        payment_processor = MultiCryptoPaymentProcessor(config, db, logger)
        
        logger.info("🚀 Starting payment monitoring service...")
        logger.info("📡 Monitoring BTC, ETH, SOL, LTC, TON payments...")
        
        # Start payment monitoring
        await payment_processor.start_payment_monitoring()
        
    except Exception as e:
        logger.error(f"Payment monitor error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 