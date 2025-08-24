#!/usr/bin/env python3
"""
Working Bot - Uses correct event loop approach
"""

import logging
import os
from dotenv import load_dotenv
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# --- Global logger setup ---
LOGGER = logging.getLogger(__name__)

async def start_command(update, context):
    """Simple start command."""
    await update.message.reply_text("🤖 Bot is running! Use /help for commands.")

async def help_command(update, context):
    """Simple help command."""
    help_text = """
🤖 **Bot Commands:**

/start - Start the bot
/help - Show this help message
/status - Check your status
/subscribe - View subscription plans

**Admin Commands:**
/admin - Admin menu
/stats - View statistics
/users - List users
/system - System status
    """
    await update.message.reply_text(help_text)

async def status_command(update, context):
    """Simple status command."""
    await update.message.reply_text("✅ Bot is online and working!")

async def subscribe_command(update, context):
    """Simple subscribe command."""
    await update.message.reply_text("💎 Subscription plans coming soon!")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Logs errors."""
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

def main():
    """Main function - let the bot handle its own event loop."""
    # --- Setup logging ---
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("logs/bot_working.log"), logging.StreamHandler()]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # --- Load environment ---
    load_dotenv('config/.env')
    bot_token = os.getenv('BOT_TOKEN')
    
    # Debug: Show what token we're using
    if bot_token:
        LOGGER.info(f"Bot token loaded: {bot_token[:10]}...{bot_token[-10:] if len(bot_token) > 20 else '***'}")
    else:
        LOGGER.error("BOT_TOKEN not found in environment")
        return
    
    # --- Build Application ---
    app = ApplicationBuilder().token(bot_token).build()

    # --- Add simple handlers ---
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    
    app.add_error_handler(error_handler)

    # --- Run the Bot ---
    LOGGER.info("Working bot is starting...")
    
    # Let the bot handle its own event loop - don't use asyncio.run()
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )

if __name__ == '__main__':
    main()
