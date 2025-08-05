#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BotConfig
from database import DatabaseManager
from ton_payments import TONPaymentProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/payment_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config/.env')

class PaymentMonitorService:
    """Automated TON payment monitoring service."""
    
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
        self.payment_processor = TONPaymentProcessor(self.config, self.db, logger)
        
    async def initialize(self):
        """Initialize database connection."""
        await self.db.initialize()
        logger.info("Payment monitor service initialized")
    
    async def run_payment_monitoring(self):
        """Run continuous payment monitoring."""
        logger.info("🔍 Starting TON payment monitoring service...")
        
        try:
            await self.initialize()
            
            while True:
                try:
                    # Get pending payments
                    async with self.db.pool.acquire() as conn:
                        pending_payments = await conn.fetch('''
                            SELECT payment_id, user_id, tier, amount_crypto, payment_memo, created_at
                            FROM payments 
                            WHERE status = 'pending' AND cryptocurrency = 'ton' AND expires_at > CURRENT_TIMESTAMP
                        ''')
                    
                    if pending_payments:
                        logger.info(f"🔍 Checking {len(pending_payments)} pending payments...")
                        
                        for payment in pending_payments:
                            payment_data = dict(payment)
                            
                            # Check if payment was received
                            payment_found = await self.payment_processor.verify_payment_on_blockchain(payment_data)
                            
                            if payment_found:
                                # Update payment status
                                await self.db.update_payment_status(payment_data['payment_id'], 'completed')
                                
                                # Activate subscription
                                await self.db.activate_subscription(
                                    payment_data['user_id'], 
                                    payment_data['tier'], 
                                    duration_days=30
                                )
                                
                                logger.info(f"✅ Payment verified and subscription activated: {payment_data['payment_id']}")
                                
                                # Send notification to user (optional)
                                try:
                                    from telegram import Bot
                                    bot = Bot(token=self.config.bot_token)
                                    await bot.send_message(
                                        chat_id=payment_data['user_id'],
                                        text="✅ **Payment Confirmed!**\n\nYour subscription is now active. Use /my_ads to manage your ad campaigns.",
                                        parse_mode='Markdown'
                                    )
                                except Exception as e:
                                    logger.error(f"Error sending notification to user: {e}")
                    
                    # Process expired payments
                    await self.payment_processor.process_expired_payments()
                    
                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"Error in payment monitoring cycle: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Payment monitoring stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in payment monitoring: {e}")
        finally:
            await self.db.close()

async def main():
    """Main function to run payment monitoring service."""
    monitor = PaymentMonitorService()
    await monitor.run_payment_monitoring()

if __name__ == '__main__':
    asyncio.run(main()) 