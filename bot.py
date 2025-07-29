#!/usr/bin/env python3
import logging
import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters, ConversationHandler, MessageHandler
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('config/.env')

# Import our modules
from config import BotConfig
from database import DatabaseManager
from crypto_payments import CryptoPaymentProcessor
from security import SecurityManager
from enhanced_ui import EnhancedUI
from enhanced_admin import AdminDashboard
from monetization import MonetizationEngine

# Import command handlers
from commands import user_commands, admin_commands, forwarding_commands

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ForwardingBot:
    def __init__(self):
        # Load configuration
        self.config = BotConfig.load_from_env()
        
        # Initialize components
        self.db = DatabaseManager(self.config, logger)
        self.security = SecurityManager(self.config, self.db, logger)
        self.ui = EnhancedUI(self.config)
        self.payments = CryptoPaymentProcessor(self.config, self.db, logger)
        self.admin = AdminDashboard(self.db, self.config, logger)
        self.monetization = MonetizationEngine(self.db, self.config, logger)
        
        # Initialize application
        self.app = Application.builder().token(self.config.bot_token).build()
        
        # Store references in bot_data
        self.app.bot_data.update({
            'db': self.db,
            'config': self.config,
            'security': self.security,
            'ui': self.ui,
            'payments': self.payments,
            'admin': self.admin,
            'monetization': self.monetization,
            'logger': logger
        })
        
    def setup_handlers(self):
        """Set up all command and message handlers."""
        # User commands
        self.app.add_handler(CommandHandler("start", user_commands.start))
        self.app.add_handler(CommandHandler("help", user_commands.help_command))
        self.app.add_handler(CommandHandler("subscribe", user_commands.subscribe))
        self.app.add_handler(CommandHandler("status", user_commands.status))

        # Handlers for ReplyKeyboardMarkup buttons
        self.app.add_handler(MessageHandler(filters.Regex('^Subscribe Now$'), user_commands.subscribe))
        self.app.add_handler(MessageHandler(filters.Regex('^How It Works$'), user_commands.how_it_works))
        self.app.add_handler(MessageHandler(filters.Regex('^Pricing$'), user_commands.pricing))
        self.app.add_handler(MessageHandler(filters.Regex('^Support$'), user_commands.support))
       
        # Autofarming commands
        self.app.add_handler(CommandHandler("set_ad", user_commands.set_ad))
        self.app.add_handler(CommandHandler("my_ad", user_commands.my_ad))
        self.app.add_handler(CommandHandler("set_schedule", user_commands.set_schedule))
        self.app.add_handler(CommandHandler("pause_ad", user_commands.pause_ad))
        self.app.add_handler(CommandHandler("resume_ad", user_commands.resume_ad))

        # --- Conversation handler for adding a destination ---
        add_dest_handler = ConversationHandler(
            entry_points=[CommandHandler("add_destination", forwarding_commands.add_destination)],
            states={
                forwarding_commands.WAITING_FORWARD: [
                    MessageHandler(filters.FORWARDED, forwarding_commands.receive_forwarded_message)
                ]
            },
            fallbacks=[CommandHandler("cancel", forwarding_commands.cancel)],
        )
        self.app.add_handler(add_dest_handler)
        
        # We also need a handler for the top-level /cancel command
        self.app.add_handler(CommandHandler("cancel", user_commands.cancel))

        # Other forwarding commands
        self.app.add_handler(CommandHandler("list_destinations", forwarding_commands.list_destinations))
        self.app.add_handler(CommandHandler("remove_destination", forwarding_commands.remove_destination))
        
        # Admin commands
        self.app.add_handler(CommandHandler("admin", admin_commands.admin_panel))
        self.app.add_handler(CommandHandler("broadcast", admin_commands.broadcast))
        self.app.add_handler(CommandHandler("stats", admin_commands.stats))
        
        # Callback query handler for buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for forwarding (must be last)
        # self.app.add_handler(MessageHandler(
        #     filters.ALL & ~filters.COMMAND,
        #     forwarding_commands.handle_message
        # ))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
    async def handle_callback(self, update: Update, context):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Route callbacks to appropriate handlers
        if data.startswith("view_tier:") or data == "main_menu":
            await user_commands.handle_subscription_callback(update, context)
        elif data.startswith("pay:"):
            await user_commands.handle_payment_callback(update, context)
        elif data.startswith("admin:"):
            await admin_commands.handle_admin_callback(update, context)
        elif data.startswith("dest:"):
            await forwarding_commands.handle_destination_callback(update, context)
        else:
            await query.edit_message_text("Invalid action.")
    
    async def error_handler(self, update: Update, context):
        """Handle errors in the bot."""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Notify user of error
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "An error occurred. Please try again or contact support."
                )
            except:
                pass
        
        # Notify admin
        if self.config.admin_id:
            try:
                error_msg = f"Error in bot:\n\n{str(context.error)}\n\nUpdate: {str(update)}"
                await context.bot.send_message(self.config.admin_id, error_msg[:4000])
            except:
                pass
    
    async def post_init(self, app: Application):
        """Initialize database and other services."""
        logger.info("Initializing bot services...")
        await self.db.initialize()
        logger.info("Bot initialization complete!")
    
    async def shutdown(self, app: Application):
        """Cleanup on shutdown."""
        logger.info("Shutting down bot...")
        await self.db.close()
    
    def run(self):
        """Run the bot."""
        try:
            # Setup handlers
            self.setup_handlers()
            
            # Add post-init and shutdown
            self.app.post_init = self.post_init
            self.app.post_shutdown = self.shutdown
            
            logger.info(f"Starting bot...")
            logger.info(f"Admin ID: {self.config.admin_id}")
            
            # Run the bot
            self.app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

def main():
    """Main entry point."""
    # Create required directories
    for directory in ['logs', 'data', 'backups']:
        os.makedirs(directory, exist_ok=True)
    
    # Create and run bot
    bot = ForwardingBot()
    bot.run()

if __name__ == '__main__':
    main()