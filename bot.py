#!/usr/bin/env python3
import logging
import os
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('config/.env')

from config import BotConfig
from database import DatabaseManager
from commands import user_commands
from commands import admin_commands

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoFarmingBot:
    def __init__(self):
        self.config = BotConfig.load_from_env()
        self.db = DatabaseManager(self.config, logger)
        self.app = Application.builder().token(self.config.bot_token).build()
        self.app.bot_data.update({'db': self.db, 'config': self.config, 'logger': logger})

    def setup_handlers(self):
        """Set up all command and message handlers."""

        # --- Conversation Handlers ---
        set_content_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(user_commands.set_content_start, pattern='^set_content:.*$')],
            states={user_commands.SETTING_AD_CONTENT: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, user_commands.set_content_receive)]},
            fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
            per_chat=True
        )
        set_schedule_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(user_commands.set_schedule_start, pattern='^set_schedule:.*$')],
            states={user_commands.SETTING_AD_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_commands.set_schedule_receive)]},
            fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
            per_chat=True
        )
        set_destinations_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(user_commands.set_destinations_start, pattern='^set_dests:.*$')],
            states={user_commands.SETTING_AD_DESTINATIONS: [CallbackQueryHandler(user_commands.select_destination_category, pattern='^select_category:.*$')]},
            fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
            per_chat=True
        )
        self.app.add_handler(set_content_conv)
        self.app.add_handler(set_schedule_conv)
        self.app.add_handler(set_destinations_conv)

        # --- Main Commands ---
        self.app.add_handler(CommandHandler("my_ads", user_commands.my_ads_command))
        self.app.add_handler(CommandHandler("start", user_commands.start))
        self.app.add_handler(CommandHandler("help", user_commands.help_command))
        self.app.add_handler(CommandHandler("subscribe", user_commands.subscribe))
        self.app.add_handler(CommandHandler("analytics", user_commands.analytics_command))
        self.app.add_handler(CommandHandler("referral", user_commands.referral_command))
        
        # --- Admin Commands ---
        self.app.add_handler(CommandHandler("add_group", admin_commands.add_group))
        self.app.add_handler(CommandHandler("list_groups", admin_commands.list_groups))
        self.app.add_handler(CommandHandler("remove_group", admin_commands.remove_group))
        self.app.add_handler(CommandHandler("admin_stats", admin_commands.admin_stats))
        self.app.add_handler(CommandHandler("verify_payment", admin_commands.verify_payment))
        self.app.add_handler(CommandHandler("revenue_stats", admin_commands.revenue_stats))
        self.app.add_handler(CommandHandler("pending_payments", admin_commands.pending_payments))

        # --- General Callback Handler for other buttons ---
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # --- Error Handler ---
        self.app.add_error_handler(self.error_handler)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        if data.startswith("manage_slot:") or data == "back_to_slots" or data.startswith("toggle_ad:"):
            await user_commands.handle_ad_slot_callback(update, context)
        elif data.startswith("subscribe:") or data.startswith("pay:") or data.startswith("check_payment:"):
            await user_commands.handle_subscription_callback(update, context)
        elif data.startswith("cmd:"):
            await user_commands.handle_command_callback(update, context)
        elif data.startswith("select_category:"):
            await user_commands.select_destination_category(update, context)
        else:
            await query.answer("This feature is coming soon!")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    async def post_init(self, app: Application):
        logger.info("Initializing bot services...")
        await self.db.initialize()
        logger.info("Bot initialization complete!")

    async def shutdown(self, app: Application):
        logger.info("Shutting down bot...")
        await self.db.close()

    def run(self):
        """Run the bot."""
        lock_file = "bot.lock"
        if os.path.exists(lock_file):
            logger.error("Lock file exists. Another instance may be running. Exiting.")
            return
        try:
            with open(lock_file, "w") as f: f.write(str(os.getpid()))
            self.setup_handlers()
            self.app.post_init = self.post_init
            self.app.post_shutdown = self.shutdown
            logger.info(f"Starting bot...")
            self.app.run_polling(drop_pending_updates=True)
        finally:
            if os.path.exists(lock_file): os.remove(lock_file)
            logger.info("Lock file removed. Bot shut down cleanly.")

if __name__ == '__main__':
    bot = AutoFarmingBot()
    bot.run()