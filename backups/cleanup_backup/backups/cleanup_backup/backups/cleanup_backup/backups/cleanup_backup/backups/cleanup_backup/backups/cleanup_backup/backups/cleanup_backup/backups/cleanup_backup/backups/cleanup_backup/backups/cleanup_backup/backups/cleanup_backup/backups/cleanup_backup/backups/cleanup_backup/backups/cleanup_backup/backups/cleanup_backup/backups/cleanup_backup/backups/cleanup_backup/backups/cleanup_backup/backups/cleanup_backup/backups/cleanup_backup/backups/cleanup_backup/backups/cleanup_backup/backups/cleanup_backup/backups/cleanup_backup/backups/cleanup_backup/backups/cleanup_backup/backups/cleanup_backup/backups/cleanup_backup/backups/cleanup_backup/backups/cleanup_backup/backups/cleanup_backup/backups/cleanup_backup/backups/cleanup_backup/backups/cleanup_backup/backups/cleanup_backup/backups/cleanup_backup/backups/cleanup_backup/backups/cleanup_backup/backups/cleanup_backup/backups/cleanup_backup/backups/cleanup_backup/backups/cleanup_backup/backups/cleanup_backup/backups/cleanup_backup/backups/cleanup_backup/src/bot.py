import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

from .config import BotConfig
from .database import DatabaseManager
from .blockchain_payments import BlockchainPaymentProcessor
from .notifications import NotificationManager
from .error_logger import TelegramErrorLogger
from .forwarding import MessageForwarder
from .filters import MessageFilter
from .commands import user, admin, forwarding as fwd_cmds

# --- Global logger setup ---
LOGGER = logging.getLogger(__name__)

async def post_init(application: Application):
    """Runs after the bot is initialized but before polling starts."""
    await application.bot.set_my_commands([
        ('start', 'Start the bot'), ('settings', 'Open settings'),
        ('help', 'Show help'), ('subscribe', 'View subscription plans'),
        ('status', 'Check subscription status'), ('list_destinations', 'View destinations'),
        ('set_alias', 'Rename a destination'), ('cancel', 'Cancel operation'),
    ])
    LOGGER.info("Custom bot commands have been set.")
    # Initialize database right after bot is ready
    await application.bot_data['db'].initialize()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Logs errors and notifies the admin."""
    LOGGER.error("Exception while handling an update:", exc_info=context.error)
    if 'error_logger' in context.bot_data:
        await context.bot_data['error_logger'].notify(context.error)

async def main() -> None:
    """Initializes and runs the bot."""
    # --- Build Application ---
    config = BotConfig.load_from_env()
    app = ApplicationBuilder().token(config.bot_token).post_init(post_init).build()

    # --- Initialize Components now that the event loop is running ---
    db = DatabaseManager("bot_database.db", LOGGER)
    notifier = NotificationManager(app.bot, LOGGER)
    payments = BlockchainPaymentProcessor(db, notifier, config, LOGGER)
    message_filter = MessageFilter(LOGGER)
    forwarder = MessageForwarder(db, config, LOGGER, message_filter)

    app.bot_data.update({
        'db': db, 'config': config, 'payments': payments,
        'notifier': notifier, 'forwarder': forwarder, 'logger': LOGGER,
        'error_logger': TelegramErrorLogger(config.admin_id, app.bot, LOGGER)
    })

    # --- Handlers ---
    alias_handler = ConversationHandler(
        entry_points=[CommandHandler("set_alias", user.set_alias_start)],
        states={
            user.ASK_ALIAS_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, user.ask_alias_name)],
            user.ASK_ALIAS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user.save_alias)],
        },
        fallbacks=[CommandHandler("cancel", user.cancel), MessageHandler(filters.Regex(r'(?i)^cancel$'), user.cancel)],
        conversation_timeout=120
    )

    app.add_error_handler(error_handler)
    app.add_handler(alias_handler)

    command_handlers = {
        "start": user.start, "help": user.help_command, "subscribe": user.subscribe,
        "status": user.status, "cancel": user.cancel, "settings": user.settings_menu,
        "list_destinations": fwd_cmds.list_destinations, "add_destination": fwd_cmds.add_destination,
        "broadcast": admin.broadcast, "stats": admin.stats, "user": admin.user_info
    }
    for command, handler in command_handlers.items():
        app.add_handler(CommandHandler(command, handler))

    callback_handlers = {
        '^start_subscribe$': user.subscribe, '^start_help$': user.help_command,
        '^subscribe_': user.subscribe, '^settings_status$': user.status,
        '^settings_destinations$': fwd_cmds.list_destinations, r'^remove_dest_': fwd_cmds.remove_destination_callback,
        '^add_destination_shortcut$': fwd_cmds.add_destination, '^cancel_action$': user.cancel
    }
    for pattern, handler in callback_handlers.items():
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, forwarder.handle_edited_message))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forwarder.handle_message))

    # --- Run the Bot ---
    try:
        LOGGER.info("Bot is starting...")
        await payments.start_monitoring()
        await app.run_polling()
    finally:
        await payments.stop_monitoring()

if __name__ == '__main__':
    # --- Load Config and Logger at the start ---
    load_dotenv('config/.env')
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("logs/bot.log"), logging.StreamHandler()]
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Bot stopped.")
