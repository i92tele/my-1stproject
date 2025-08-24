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
from src.database.manager import DatabaseManager
from crypto_payments import CryptoPaymentProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MaintenanceService:
    """Automated maintenance tasks for the bot."""
    
    def __init__(self):
        load_dotenv('config/.env')
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
        self.payment_processor = CryptoPaymentProcessor(self.config, self.db, logger)
    
    async def initialize(self):
        """Initialize database connection."""
        await self.db.initialize()
        logger.info("Maintenance service initialized")
    
    async def cleanup_expired_subscriptions(self):
        """Deactivate expired subscriptions."""
        try:
            expired_count = await self.db.deactivate_expired_subscriptions()
            if expired_count > 0:
                logger.info(f"Deactivated {expired_count} expired subscriptions")
            else:
                logger.info("No expired subscriptions found")
        except Exception as e:
            logger.error(f"Error cleaning up expired subscriptions: {e}")
    
    async def cleanup_expired_payments(self):
        """Process expired payments."""
        try:
            await self.payment_processor.process_expired_payments()
            logger.info("Expired payments processed")
        except Exception as e:
            logger.error(f"Error processing expired payments: {e}")
    
    async def generate_daily_report(self):
        """Generate daily revenue and usage report."""
        try:
            # Get payment statistics
            payment_stats = await self.payment_processor.get_payment_statistics()
            
            # Get bot statistics
            bot_stats = await self.db.get_bot_statistics()
            
            # Get expired subscriptions
            expired_subs = await self.db.get_expired_subscriptions()
            
            report = f"""
📊 **Daily Maintenance Report** - {datetime.now().strftime('%Y-%m-%d')}

💰 **Revenue Statistics:**
• Total Payments: {payment_stats.get('total_payments', 0)}
• Completed Payments: {payment_stats.get('completed_payments', 0)}
• Total Revenue: ${payment_stats.get('total_revenue', 0):.2f}

👥 **User Statistics:**
• Total Users: {bot_stats.get('total_users', 0)}
• Active Subscriptions: {bot_stats.get('active_subscriptions', 0)}
• Expired Subscriptions: {len(expired_subs)}

📈 **Revenue by Cryptocurrency:**
"""
            
            for crypto_revenue in payment_stats.get('revenue_by_crypto', []):
                report += f"• {crypto_revenue['cryptocurrency'].upper()}: ${crypto_revenue['total_usd']:.2f} ({crypto_revenue['count']} payments)\n"
            
            logger.info("Daily report generated")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return "Error generating report"
    
    async def run_maintenance_cycle(self):
        """Run all maintenance tasks."""
        logger.info("🔄 Starting maintenance cycle...")
        
        try:
            # Cleanup expired subscriptions
            await self.cleanup_expired_subscriptions()
            
            # Cleanup expired payments
            await self.cleanup_expired_payments()
            
            # Generate daily report
            report = await self.generate_daily_report()
            logger.info("✅ Maintenance cycle completed")
            
            return report
            
        except Exception as e:
            logger.error(f"Error in maintenance cycle: {e}")
            return None
    
    async def run_scheduled_maintenance(self):
        """Run maintenance on a schedule."""
        logger.info("🚀 Starting scheduled maintenance service...")
        
        try:
            await self.initialize()
            
            while True:
                try:
                    await self.run_maintenance_cycle()
                    
                    # Wait 24 hours before next maintenance cycle
                    logger.info("💤 Sleeping for 24 hours...")
                    await asyncio.sleep(24 * 60 * 60)  # 24 hours
                    
                except Exception as e:
                    logger.error(f"Error in scheduled maintenance: {e}")
                    await asyncio.sleep(60 * 60)  # Wait 1 hour on error
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Maintenance service stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in maintenance service: {e}")
        finally:
            await self.db.close()

async def main():
    """Main function to run maintenance service."""
    maintenance = MaintenanceService()
    await maintenance.run_scheduled_maintenance()

if __name__ == '__main__':
    asyncio.run(main()) 