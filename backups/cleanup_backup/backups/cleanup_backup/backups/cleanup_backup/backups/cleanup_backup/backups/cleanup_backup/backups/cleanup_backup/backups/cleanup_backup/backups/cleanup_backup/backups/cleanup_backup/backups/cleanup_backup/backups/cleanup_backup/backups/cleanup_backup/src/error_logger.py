import logging
from datetime import datetime
from telegram import Bot, constants

class TelegramErrorLogger:
    def __init__(self, admin_id: int, bot: Bot, logger: logging.Logger):
        self.admin_id = admin_id
        self.bot = bot
        self.logger = logger

    async def notify(self, error: Exception):
        """Notify admin about an error and log it."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # This detailed log entry will now always be recorded by the main logger
        # which we will configure to write to both the console and a file.
        log_entry = f"Error handled: {error_type}: {error_message}"
        self.logger.error(log_entry, exc_info=True)
        
        # The message sent to the admin is a simpler summary.
        message = f"🚨 <b>Bot Error:</b>\n\n<code>{error_type}</code>: {error_message}"
        
        try:
            await self.bot.send_message(self.admin_id, message, parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            # Log the failure to notify the admin
            self.logger.error(f"CRITICAL: Failed to send error notification to admin {self.admin_id}. Error: {e}")