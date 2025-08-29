import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

from src.config.bot_config import BotConfig
from src.database.manager import DatabaseManager
from multi_crypto_payments import MultiCryptoPaymentProcessor
from src.notifications import NotificationManager
from src.error_logger import TelegramErrorLogger
from src.forwarding import MessageForwarder
from src.filters import MessageFilter
from commands import user_commands as user, admin_commands as admin, forwarding_commands as fwd_cmds, suggestion_commands as suggestions, subscription_commands as subs, admin_slot_commands as admin_slots
from src.ui_manager import initialize_ui_manager

# --- Global logger setup ---
LOGGER = logging.getLogger(__name__)

# Background tasks
background_tasks = []

async def post_init(application: Application):
    """Runs after the bot is initialized but before polling starts."""
    await application.bot.set_my_commands([
        ('start', 'Start the bot'), ('help', 'Show help'), 
        ('subscribe', 'View subscription plans'), ('status', 'Check subscription status'), 
        ('list_destinations', 'View destinations'), ('add_destination', 'Add destination'),
        ('suggestions', 'Submit suggestions'), ('analytics', 'View analytics'),
        ('cancel', 'Cancel operation'),
        # Admin commands
        ('admin', 'Admin menu'), ('admin_menu', 'Admin menu'), ('stats', 'Admin statistics'),
        ('user', 'List users'), ('system', 'System status'), ('workers', 'Worker status'),
        ('revenue', 'Revenue statistics'), ('payments', 'Pending payments'), ('health', 'Health check'),
        ('admin_slots', 'Admin ad slots'), ('admin_slot_stats', 'Admin slot statistics'),
    ])
    LOGGER.info("Custom bot commands have been set.")
    # Database will be initialized after components are added to bot_data

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Logs errors and notifies the admin."""
    LOGGER.error("Exception while handling an update:", exc_info=context.error)
    if 'error_logger' in context.bot_data:
        await context.bot_data['error_logger'].notify(context.error)

# Background tasks functionality temporarily disabled to fix event loop conflicts
# Payment monitoring and scheduling will be handled by separate processes for now

# Only run if this file is executed directly (not imported)
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

    # Fixed startup - let the bot handle its own event loop
    try:
        # Load environment and get token
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            LOGGER.error("BOT_TOKEN not found in environment")
            exit(1)
        
        # Build Application
        app = ApplicationBuilder().token(bot_token).post_init(post_init).build()
        
        # Initialize components (synchronously)
        config = BotConfig.load_from_env()
        db = DatabaseManager("bot_database.db", LOGGER)
        notifier = NotificationManager(app.bot, LOGGER)
        payments = MultiCryptoPaymentProcessor(config, db, LOGGER)
        message_filter = MessageFilter(LOGGER)
        forwarder = MessageForwarder(db, config, LOGGER, message_filter)
        
        # Note: Background payment monitoring is handled by separate payment_monitor.py process
        ui_manager = initialize_ui_manager(LOGGER)
        
        app.bot_data.update({
            'db': db, 'config': config, 'payments': payments,
            'notifier': notifier, 'forwarder': forwarder, 'logger': LOGGER,
            'ui_manager': ui_manager,
            'error_logger': TelegramErrorLogger(config.admin_ids[0] if config.admin_ids else 0, app.bot, LOGGER)
        })
        
        # Initialize database tables
        db.initialize_sync()
        LOGGER.info("Components initialized successfully")

        # Add handlers
        suggestion_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(suggestions.start_suggestion_input, pattern='^submit_suggestion$')],
            states={
                suggestions.WAITING_FOR_SUGGESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, suggestions.handle_suggestion_text)],
            },
            fallbacks=[CommandHandler("cancel", user.cancel_conversation), MessageHandler(filters.Regex(r'(?i)^cancel$'), user.cancel_conversation)],
            conversation_timeout=300
        )

        # Ad content setting conversation
        ad_content_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(user.set_content_start, pattern='^set_content:')],
            states={
                user.SETTING_AD_CONTENT: [
                    CallbackQueryHandler(user.handle_content_category_selection, pattern='^category:'),
                    MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, user.set_content_receive)
                ],
            },
            fallbacks=[CommandHandler("cancel", user.cancel_conversation)],
            conversation_timeout=300
        )

        # Ad schedule setting conversation
        ad_schedule_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(user.set_schedule_start, pattern='^set_schedule:')],
            states={
                user.SETTING_AD_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user.set_schedule_receive)],
            },
            fallbacks=[CommandHandler("cancel", user.cancel_conversation)],
            conversation_timeout=300
        )

        # Ad destinations setting conversation
        ad_destinations_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(user.set_destinations_start, pattern='^set_dests:')],
            states={
                user.SETTING_AD_DESTINATIONS: [CallbackQueryHandler(user.select_destination_category, pattern='^select_category:')],
            },
            fallbacks=[CommandHandler("cancel", user.cancel_conversation)],
            conversation_timeout=300
        )

        app.add_error_handler(error_handler)
        app.add_handler(suggestion_handler)
        app.add_handler(ad_content_handler)
        app.add_handler(ad_schedule_handler)
        app.add_handler(ad_destinations_handler)

        command_handlers = {
            "start": user.start, "help": user.help_command, "subscribe": user.subscribe,
            "status": user.status, "cancel": user.cancel_conversation, "analytics": user.analytics_command,
            "list_destinations": fwd_cmds.list_destinations, "add_destination": fwd_cmds.add_destination_command,
            "suggestions": suggestions.show_suggestions_menu,
            # Admin commands
            "admin": admin.admin_menu, "admin_menu": admin.admin_menu, "stats": admin.admin_stats, 
            "user": admin.list_users, "system": admin.system_status, "workers": admin.worker_status,
            "revenue": admin.revenue_stats, "payments": admin.pending_payments, "health": admin.health_stats,
            "test_admin": admin.test_admin, "add_group": admin.add_group, "list_groups": admin.list_groups,
            "admin_stats": admin.admin_stats, "admin_warnings": admin.admin_warnings, "admin_suggestions": admin.admin_suggestions,
            # Admin slot commands
            "admin_slots": admin_slots.admin_slots, "admin_slot_stats": admin_slots.admin_slot_stats
        }
        for command, handler in command_handlers.items():
            app.add_handler(CommandHandler(command, handler))

        # Wrapper function for admin callback to extract action and parts
        async def admin_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Wrapper to extract action and parts from callback data for admin handler."""
            query = update.callback_query
            if not query or not query.data:
                return
            
            data = query.data
            if data.startswith("cmd:"):
                parts = data.split(":")
                action = parts[1] if len(parts) > 1 else ""
                await admin.handle_admin_callback(update, context, action, parts)
            else:
                # Handle other admin callbacks that start with admin:
                parts = data.split(":")
                action = parts[1] if len(parts) > 1 else ""
                await admin.handle_admin_callback(update, context, action, parts)

        # Wrapper function for user command callbacks (cmd:*)
        async def user_cmd_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Wrapper for user command callbacks starting with cmd:"""
            query = update.callback_query
            if not query or not query.data:
                return
            
            data = query.data
            if data.startswith("cmd:"):
                # Check if this is an admin command and route accordingly
                command = data.split(":")[1] if len(data.split(":")) > 1 else ""
                
                # List of admin commands that should be routed to admin handler
                admin_commands = [
                    "admin_menu", "list_users", "admin_stats", "system_check", 
                    "posting_status", "failed_groups", "paused_slots", "revenue_stats",
                    "worker_status", "system_status", "list_groups",
                    "admin_ads_analysis", "admin_warnings", "admin_suggestions"
                ]
                
                # User commands that should be routed to user handler
                user_commands = ["start", "analytics", "referral", "subscribe", "my_ads", "help", "suggestions"]
                
                if command in admin_commands:
                    # Route to admin callback handler
                    await admin_callback_wrapper(update, context)
                elif command == "admin_slots":
                    # Route to admin slot callback handler
                    await admin_slots.handle_admin_slot_callback(update, context)
                elif command in user_commands:
                    # Route to user callback handler
                    await user.handle_command_callback(update, context)
                else:
                    # Unknown command
                    LOGGER.warning(f"Unknown command: {command}")
                    await query.answer("❌ Unknown command")
                    await query.edit_message_text("❌ Unknown command")
            else:
                # This shouldn't happen but handle gracefully
                await query.answer("❌ Invalid command")
                await query.edit_message_text("❌ Invalid command")

        callback_handlers = {
            # User command callbacks (cmd:*)
            '^cmd:': user_cmd_callback_wrapper,
            # Subscription flow callbacks
            '^subscribe:': user.handle_subscription_callback,
            '^crypto:': user.handle_subscription_callback,
            '^check_payment:': user.handle_subscription_callback,
            '^cancel_payment:': user.handle_subscription_callback,
            '^copy_address:': user.handle_subscription_callback,
            '^compare_plans$': user.handle_subscription_callback,
            '^back_to_plans$': user.handle_subscription_callback,
            # Ad slot management callbacks (non-conversation)
            '^manage_slot:': user.handle_ad_slot_callback,
            '^toggle_ad:': user.handle_ad_slot_callback,
            '^back_to_slots$': user.handle_ad_slot_callback,
            '^slot_analytics:': user.handle_subscription_callback,
            # Legacy subscription handlers (cleanup needed)
            '^start_subscribe$': user.subscribe, '^start_help$': user.help_command,
            '^subscribe_': user.subscribe, '^settings_status$': user.status,
            '^settings_destinations$': fwd_cmds.list_destinations, r'^remove_dest_': fwd_cmds.handle_remove_destination_callback,
            '^add_destination_shortcut$': fwd_cmds.add_destination_command, '^cancel_action$': user.cancel_conversation,
            # Admin callbacks
            '^admin:': admin_callback_wrapper,
            # Suggestion callbacks
            '^submit_suggestion$': suggestions.start_suggestion_input,
            '^my_suggestions$': suggestions.show_user_suggestions,
            '^suggestion_stats$': suggestions.show_suggestion_stats,
            '^cancel_suggestions$': suggestions.cancel_suggestions,
            '^suggestions_menu$': suggestions.show_suggestions_menu,
            # Admin slot callbacks
            '^admin_slot': admin_slots.handle_admin_slot_callback,
            '^admin_toggle_slot:': admin_slots.handle_admin_slot_callback,
            '^admin_set_content:': admin_slots.handle_admin_slot_callback,
            '^admin_set_destinations:': admin_slots.handle_admin_slot_callback,
            '^admin_post_slot:': admin_slots.handle_admin_slot_callback,
            '^admin_delete_slot:': admin_slots.handle_admin_slot_callback,
            '^admin_slot_analytics:': admin_slots.handle_admin_slot_callback,
            '^admin_quick_post': admin_slots.handle_admin_slot_callback,
            '^admin_quick_post_send': admin_slots.handle_admin_slot_callback,
            '^admin_quick_post_template': admin_slots.handle_admin_slot_callback,
            '^admin_slots': admin_slots.handle_admin_slot_callback,
            '^admin_slots_refresh': admin_slots.handle_admin_slot_callback,
            '^admin_category:': admin_slots.handle_admin_slot_callback,
            '^admin_toggle_dest:': admin_slots.handle_admin_slot_callback,
            '^admin_select_category:': admin_slots.handle_admin_slot_callback,
            '^admin_clear_category:': admin_slots.handle_admin_slot_callback,
            '^admin_select_all:': admin_slots.handle_admin_slot_callback,
            '^admin_clear_all:': admin_slots.handle_admin_slot_callback,
            '^admin_save_destinations:': admin_slots.handle_admin_slot_callback,
            '^admin_slot_stats': admin_slots.handle_admin_slot_callback,
            '^admin_clear_all_content': admin_slots.handle_admin_slot_callback,
            '^admin_clear_all_destinations': admin_slots.handle_admin_slot_callback,
            '^admin_purge_all_slots': admin_slots.handle_admin_slot_callback,
            '^admin_confirm_purge_all_slots': admin_slots.handle_admin_slot_callback
        }
        for pattern, handler in callback_handlers.items():
            app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

        app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, forwarder.handle_edited_message))
        
        # Add admin content message handler (must come before general message handler)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_slots.handle_admin_content_message))
        
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forwarder.handle_message))

        # Run the bot - let it handle its own event loop
        LOGGER.info("Bot is starting...")
        LOGGER.info("✅ Background payment monitoring is handled by separate payment_monitor.py process")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "edited_message"]
        )
        
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Bot stopped.")
    except Exception as e:
        LOGGER.error(f"Bot startup error: {e}")
        raise
