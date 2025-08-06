import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

# Load environment variables
load_dotenv('config/.env')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update, context):
    await update.message.reply_text("Hello! Bot is working!")

async def main():
    """Simple bot that just works."""
    # Get token from environment
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN not found in environment")
        return
    
    # Create application
    app = ApplicationBuilder().token(token).build()
    
    # Add simple command handler
    app.add_handler(CommandHandler("start", start_command))
    
    logger.info("Starting simple bot...")
    
    # Run the bot
    await app.run_polling(drop_pending_updates=True)
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
