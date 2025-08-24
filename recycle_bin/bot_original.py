#!/usr/bin/env python3
import logging
import os
import sys
import asyncio
import warnings
from datetime import datetime
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(filename=None):
        # Fallback function if dotenv is not available
        pass
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

# Suppress PTB warnings about conversation handlers
warnings.filterwarnings("ignore", message=".*per_message=False.*CallbackQueryHandler.*")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('config/.env')

from config import BotConfig
from src.database.manager import DatabaseManager
from commands import user_commands
from commands import admin_commands
from commands import forwarding_commands

# Import new command modules
try:
    from commands import subscription_commands
    SUBSCRIPTION_COMMANDS_AVAILABLE = True
except ImportError:
    SUBSCRIPTION_COMMANDS_AVAILABLE = False
    logging.warning("Subscription commands not available")

try:
    from commands import user_commands
    USER_COMMANDS_AVAILABLE = True
except ImportError:
    USER_COMMANDS_AVAILABLE = False
    logging.warning("User commands not available")

try:
    from commands import admin_slot_commands
    ADMIN_SLOT_COMMANDS_AVAILABLE = True
except ImportError:
    ADMIN_SLOT_COMMANDS_AVAILABLE = False
    logging.warning("Admin slot commands not available")

# Import suggestions system
try:
    from commands.suggestion_commands import get_suggestion_handlers, show_suggestions_menu
    SUGGESTIONS_AVAILABLE = True
except ImportError:
    SUGGESTIONS_AVAILABLE = False
    logging.warning("Suggestions system not available")

# Import new classes
try:
    from src.worker_manager import WorkerManager
    from src.auto_poster import AutoPoster
    from src.payment_processor import PaymentProcessor
    from src.posting_service import PostingService
    NEW_CLASSES_AVAILABLE = True
except ImportError:
    NEW_CLASSES_AVAILABLE = False
    logging.warning("New classes not available")

# Import payment processor
try:
    from src.payment_processor import initialize_payment_processor
    PAYMENT_AVAILABLE = True
except ImportError:
    PAYMENT_AVAILABLE = False
    logging.warning("Payment processor not available")

# Import posting service
try:
    from src.posting_service import initialize_posting_service, start_posting_service_background
    POSTING_SERVICE_AVAILABLE = True
except ImportError:
    POSTING_SERVICE_AVAILABLE = False
    logging.warning("Posting service not available")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoFarmingBot:
    """Main AutoFarming Bot application.
    
    Handles Telegram bot initialization, command routing, and lifecycle management.
    """
    
    def __init__(self):
        """Initialize the AutoFarming Bot.
        
        Sets up configuration, database, application, and optional components.
        """
        try:
            # Load configuration
            self.config = BotConfig.load_from_env()
            logger.info("Configuration loaded successfully")
            
            # Initialize database
            self.db = DatabaseManager("bot_database.db", logger)
            logger.info("Database manager initialized")
            
            # Build application with timeouts
            self.app = Application.builder().token(self.config.bot_token).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).build()
            
            # Set up bot data
            self.app.bot_data.update({
                'db': self.db, 
                'config': self.config, 
                'logger': logger
            })
            logger.info("Application built successfully")
            
            # Initialize optional components
            self._initialize_optional_components()
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _initialize_optional_components(self):
        """Initialize optional components if available."""
        try:
            # Initialize new components if available
            if NEW_CLASSES_AVAILABLE:
                self.worker_manager = WorkerManager(self.db, logger)
                self.payment_processor = PaymentProcessor(self.db, logger)
                # PostingService in current implementation takes (db_manager, logger)
                self.posting_service = PostingService(self.db, logger)
                self.app.bot_data.update({
                    'worker_manager': self.worker_manager,
                    'payment_processor': self.payment_processor,
                    'posting_service': self.posting_service
                })
                logger.info("New components initialized successfully")
            else:
                self.worker_manager = None
                self.payment_processor = None
                self.posting_service = None
                logger.warning("New components not available")
            
            # Initialize payment processor if available
            if PAYMENT_AVAILABLE:
                self.payment_processor = initialize_payment_processor(self.db, logger)
                self.app.bot_data['payment_processor'] = self.payment_processor
                logger.info("Payment processor initialized")
                
                # Initialize price update service
                try:
                    from price_update_service import initialize_price_service
                    self.price_service = initialize_price_service(self.payment_processor, update_interval_minutes=5)
                    self.app.bot_data['price_service'] = self.price_service
                    logger.info("Price update service initialized")
                except Exception as e:
                    self.price_service = None
                    logger.error(f"Error initializing price service: {e}")
            else:
                self.payment_processor = None
                self.price_service = None
                logger.warning("Payment processor not available")
            
            # Initialize posting service if available
            if POSTING_SERVICE_AVAILABLE:
                self.posting_service = initialize_posting_service(self.db, logger)
                self.app.bot_data['posting_service'] = self.posting_service
                logger.info("Posting service initialized")
            else:
                self.posting_service = None
                logger.warning("Posting service not available")
            
            # Initialize notification scheduler
            try:
                from notification_scheduler import NotificationScheduler
                self.notification_scheduler = NotificationScheduler(self.app.bot, self.db, logger)
                self.app.bot_data['notification_scheduler'] = self.notification_scheduler
                logger.info("Notification scheduler initialized")
                
                # Note: Notification scheduler will be started when the bot starts
                # asyncio.create_task() removed to avoid "no running event loop" error
                logger.info("Notification scheduler ready to start")
            except ImportError:
                self.notification_scheduler = None
                logger.warning("Notification scheduler not available")
            except Exception as e:
                self.notification_scheduler = None
                logger.error(f"Error initializing notification scheduler: {e}")
                
        except Exception as e:
            logger.error(f"Error initializing optional components: {e}")
            # Continue without optional components

    def setup_handlers(self):
        """Set up all command and message handlers.
        
        Configures conversation handlers, command handlers, and error handlers.
        """
        try:
            # --- Conversation Handlers ---
            set_content_conv = ConversationHandler(
                entry_points=[CallbackQueryHandler(user_commands.set_content_start, pattern='^set_content:.*$')],
                states={
                    user_commands.SETTING_AD_CONTENT: [
                        MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, user_commands.set_content_receive),
                        CallbackQueryHandler(user_commands.handle_content_category_selection, pattern='^category:.*$')
                    ]
                },
                fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
                per_chat=True,
                per_message=False,  # Changed to False to allow MessageHandler
                per_user=False
            )
            set_schedule_conv = ConversationHandler(
                entry_points=[CallbackQueryHandler(user_commands.set_schedule_start, pattern='^set_schedule:.*$')],
                states={user_commands.SETTING_AD_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_commands.set_schedule_receive)]},
                fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
                per_chat=True,
                per_message=False,
                per_user=False
            )
            set_destinations_conv = ConversationHandler(
                entry_points=[CallbackQueryHandler(user_commands.set_destinations_start, pattern='^set_dests:.*$')],
                states={user_commands.SETTING_AD_DESTINATIONS: [CallbackQueryHandler(user_commands.select_destination_category, pattern='^select_category:.*$')]},
                fallbacks=[CommandHandler('cancel', user_commands.cancel_conversation)],
                per_chat=True,
                per_message=False,
                per_user=False
            )
            
            # --- Main Commands ---
            self.app.add_handler(CommandHandler("my_ads", user_commands.my_ads_command))
            self.app.add_handler(CommandHandler("start", user_commands.start))
            self.app.add_handler(CommandHandler("help", user_commands.help_command))
            self.app.add_handler(CommandHandler("subscribe", user_commands.subscribe))
            self.app.add_handler(CommandHandler("analytics", user_commands.analytics_command))
            self.app.add_handler(CommandHandler("referral", user_commands.referral_command))
            self.app.add_handler(CommandHandler("status", user_commands.status))
            # Bulk add groups command for admins
            self.app.add_handler(CommandHandler("bulk_add_groups", admin_commands.bulk_add_groups))
            # Built-in health checks (no terminal needed)
            self.app.add_handler(CommandHandler("system_check", admin_commands.system_check))
            self.app.add_handler(CommandHandler("scheduler_check", admin_commands.scheduler_check))
            self.app.add_handler(CommandHandler("schema_check", admin_commands.schema_check))
            self.app.add_handler(CommandHandler("fix_payment", admin_commands.fix_payment))
            self.app.add_handler(CommandHandler("test_pricing", admin_commands.test_pricing))
            self.app.add_handler(CommandHandler("delete_test_user", admin_commands.delete_test_user))
            logger.info("Main command handlers configured")
            
            # --- Forwarding Commands ---
            self.app.add_handler(CommandHandler("add_destination", forwarding_commands.add_destination_command))
            self.app.add_handler(CommandHandler("list_destinations", forwarding_commands.list_destinations))
            self.app.add_handler(CommandHandler("remove_destination", forwarding_commands.remove_destination))
            logger.info("Forwarding command handlers configured")
            
            # --- Admin Commands ---
            self.app.add_handler(CommandHandler("add_group", admin_commands.add_group))
            self.app.add_handler(CommandHandler("list_groups", admin_commands.list_groups))
            self.app.add_handler(CommandHandler("remove_group", admin_commands.remove_group))
            self.app.add_handler(CommandHandler("admin_stats", admin_commands.admin_stats))
            self.app.add_handler(CommandHandler("posting_status", admin_commands.posting_service_status))
            self.app.add_handler(CommandHandler("verify_payment", admin_commands.verify_payment))
            self.app.add_handler(CommandHandler("revenue_stats", admin_commands.revenue_stats))
            self.app.add_handler(CommandHandler("pending_payments", admin_commands.pending_payments))
            self.app.add_handler(CommandHandler("worker_status", admin_commands.worker_status))
            self.app.add_handler(CommandHandler("admin_warnings", admin_commands.admin_warnings))
            self.app.add_handler(CommandHandler("increase_limits", admin_commands.increase_worker_limits))
            self.app.add_handler(CommandHandler("capacity_check", admin_commands.worker_capacity_check))
            self.app.add_handler(CommandHandler("activate_subscription", admin_commands.activate_subscription))
            self.app.add_handler(CommandHandler("list_users", admin_commands.list_users))
            self.app.add_handler(CommandHandler("admin_menu", admin_commands.admin_menu))
            
            # --- Admin Suggestions Command ---
            # Note: admin_suggestions is now handled by the suggestions system
            # if SUGGESTIONS_AVAILABLE:
            #     self.app.add_handler(CommandHandler("admin_suggestions", admin_commands.admin_suggestions))
            
            # --- New Subscription Commands ---
            if SUBSCRIPTION_COMMANDS_AVAILABLE:
                self.app.add_handler(CommandHandler("upgrade_subscription", subscription_commands.upgrade_subscription))
                self.app.add_handler(CommandHandler("prolong_subscription", subscription_commands.prolong_subscription))
                logger.info("Subscription commands registered")
            
            # --- New Admin Slot Commands ---
            if ADMIN_SLOT_COMMANDS_AVAILABLE:
                self.app.add_handler(CommandHandler("admin_slots", admin_slot_commands.admin_slots))
                logger.info("Admin slot commands registered")
            
            # --- Suggestions System ---
            if SUGGESTIONS_AVAILABLE:
                logger.info("Registering suggestions system handlers...")
                suggestion_handlers = get_suggestion_handlers()
                logger.info(f"Got {len(suggestion_handlers)} suggestion handlers")
                for i, handler in enumerate(suggestion_handlers):
                    self.app.add_handler(handler)
                    logger.info(f"Registered suggestion handler {i+1}: {type(handler).__name__}")
                logger.info("Suggestions system handlers registered successfully")
            else:
                logger.warning("Suggestions system not available - handlers not registered")
            
            self.app.add_handler(CommandHandler("test_admin", admin_commands.test_admin))
            self.app.add_handler(CommandHandler("fix_user_slots", admin_commands.fix_user_slots))
            self.app.add_handler(CommandHandler("failed_groups", admin_commands.failed_groups))
            self.app.add_handler(CommandHandler("retry_group", admin_commands.retry_group))
            self.app.add_handler(CommandHandler("paused_slots", admin_commands.paused_slots))
            self.app.add_handler(CommandHandler("redistribute_workers", admin_commands.redistribute_workers))
            self.app.add_handler(CommandHandler("worker_distribution", admin_commands.worker_distribution))
            logger.info("Admin command handlers configured")

            # --- Conversation Handlers (must be before general callback handler) ---
            self.app.add_handler(set_content_conv)
            self.app.add_handler(set_schedule_conv)
            self.app.add_handler(set_destinations_conv)
            logger.info("Conversation handlers configured")

            # --- General Callback Handler for other buttons ---
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))

            # --- Error Handler ---
            self.app.add_error_handler(self.error_handler)
            logger.info("Error handler configured")

            # --- Admin Text Input Handler for inline flows (non-blocking) ---
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_commands.handle_admin_text, block=False))
            
        except Exception as e:
            logger.error(f"Error setting up handlers: {e}")
            raise

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards.
        
        Args:
            update: Telegram update object
            context: Bot context
            
        Returns:
            None
        """
        try:
            query = update.callback_query
            if not query or not query.data:
                logger.error("Invalid callback query")
                return
                
            data = query.data
            
            # Import user commands for all user-related callbacks
            try:
                from commands import user_commands
            except ImportError:
                logger.error("User commands not available")
                await query.edit_message_text("❌ User features not available")
                return
            
            # Add small delay to prevent rapid-fire requests
            await asyncio.sleep(0.1)
            
            # Route callbacks to appropriate handlers
            if data.startswith("manage_slot:") or data == "back_to_slots" or data.startswith("toggle_ad:"):
                await user_commands.handle_ad_slot_callback(update, context)
            elif data.startswith("subscribe:") or data.startswith("pay:") or data.startswith("check_payment:") or data.startswith("cancel_payment:") or data.startswith("copy_address:"):
                await user_commands.handle_subscription_callback(update, context)
            elif data.startswith("cmd:"):
                # Handle command callbacks
                command = data.split(":")[1]
                logger.info(f"Command callback: {command}")
                
                if command == "start":
                    await user_commands.start_callback(update, context)
                elif command == "admin_menu":
                    try:
                        from commands import admin_commands
                        await admin_commands.admin_menu(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "admin_suggestions":
                    # Admin suggestions is handled by the suggestions system
                    await query.answer("Admin suggestions feature moved to suggestions system")
                elif command == "system_status":
                    # Import admin commands to handle system status
                    try:
                        from commands import admin_commands
                        await admin_commands.system_status(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "list_users":
                    try:
                        from commands import admin_commands
                        await admin_commands.list_users(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "list_groups":
                    try:
                        from commands import admin_commands
                        await admin_commands.list_groups(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "admin_stats":
                    try:
                        from commands import admin_commands
                        await admin_commands.admin_stats(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "admin_slots":
                    try:
                        from commands import admin_slot_commands
                        await admin_slot_commands.admin_slots(update, context)
                    except ImportError:
                        logger.warning("Admin slot commands not available")
                        await query.edit_message_text("❌ Admin slot features not available")
                elif command == "admin_ads_analysis":
                    try:
                        from commands import admin_slot_commands
                        await admin_slot_commands.admin_slot_stats(update, context)
                    except ImportError:
                        logger.warning("Admin slot commands not available")
                        await query.edit_message_text("❌ Admin ads analysis not available")
                elif command == "posting_status":
                    try:
                        from commands import admin_commands
                        await admin_commands.posting_service_status(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "worker_status":
                    try:
                        from commands import admin_commands
                        await admin_commands.worker_status(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "system_check":
                    try:
                        from commands import admin_commands
                        await admin_commands.system_check(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "failed_groups":
                    try:
                        from commands import admin_commands
                        await admin_commands.failed_groups(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "paused_slots":
                    try:
                        from commands import admin_commands
                        await admin_commands.paused_slots(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                elif command == "revenue_stats":
                    try:
                        from commands import admin_commands
                        await admin_commands.revenue_stats(update, context)
                    except ImportError:
                        logger.warning("Admin commands not available")
                        await query.edit_message_text("❌ Admin features not available")
                # Handle user commands
                elif command in ["analytics", "subscribe", "help", "my_ads", "referral"]:
                    try:
                        # Create a mock callback query data in the expected format
                        class MockCallbackQuery:
                            def __init__(self, data, original_query):
                                self.data = data
                                self.original_query = original_query  # Store the original query
                                self.from_user = original_query.from_user
                                self.message = original_query.message
                                self.inline_message_id = original_query.inline_message_id
                                self.chat_instance = original_query.chat_instance
                                self.game_short_name = original_query.game_short_name
                            
                            async def answer(self, *args, **kwargs):
                                return await self.original_query.answer(*args, **kwargs)
                            
                            async def edit_message_text(self, *args, **kwargs):
                                return await self.original_query.edit_message_text(*args, **kwargs)
                        
                        class MockUpdate:
                            def __init__(self):
                                self.callback_query = MockCallbackQuery(f"cmd:{command}", update.callback_query)
                                self.effective_user = update.effective_user
                                self.effective_chat = update.effective_chat
                                self.message = update.message
                        
                        mock_update = MockUpdate()
                        await user_commands.handle_command_callback(mock_update, context)
                        
                    except AttributeError as e:
                        logger.warning(f"User command function not found: {e}")
                        await query.edit_message_text(f"❌ {command.title()} feature not available")
                else:
                    await query.answer("This command is not implemented yet!")
                    logger.warning(f"Unknown command callback: {command}")
            elif data.startswith("crypto:"):
                await user_commands.handle_crypto_selection_callback(update, context)
            elif data.startswith("select_category:"):
                await user_commands.select_destination_category(update, context)
            elif data.startswith("remove_dest:"):
                await forwarding_commands.handle_remove_destination_callback(update, context)
            elif data.startswith("dest:"):
                await forwarding_commands.handle_destinations_callback(update, context)
            elif data.startswith("admin:"):
                logger.info(f"Admin callback received: {data}")
                await self._handle_admin_callback(update, context, data)
            elif data == "compare_plans":
                await user_commands.compare_plans_callback(update, context)
            elif data == "help":
                await user_commands.help_command_callback(update, context)
            elif data.startswith("slot:"):
                await user_commands.handle_ad_slot_callback(update, context)
            elif data.startswith("category:"):
                # Parse category callback data: category:{slot_id}:{category}
                parts = data.split(":")
                if len(parts) == 3:
                    slot_id = parts[1]
                    category = parts[2]
                    await user_commands.handle_category_selection(update, context, slot_id, category)
                else:
                    await query.answer("Invalid category selection")
                    logger.warning(f"Invalid category callback data: {data}")
            elif data.startswith("set_content:"):
                if USER_COMMANDS_AVAILABLE:
                    try:
                        await user_commands.set_content_start(update, context)
                    except Exception as e:
                        logger.error(f"Error in set_content callback: {e}")
                        await query.answer("Error setting ad content")
                else:
                    await query.answer("User commands not available")
            elif data.startswith("cancel_payment:") or data.startswith("copy_address:") or data.startswith("check_payment:"):
                await user_commands.handle_subscription_callback(update, context)
            elif data.startswith("upgrade:") or data.startswith("prolong:") or data.startswith("check_upgrade_payment:") or data.startswith("check_prolong_payment:"):
                if SUBSCRIPTION_COMMANDS_AVAILABLE:
                    await subscription_commands.handle_subscription_callback(update, context)
                else:
                    await query.answer("Subscription features not available")
            elif data.startswith("admin_slot:") or data.startswith("admin_quick_post") or data.startswith("admin_post_slot:") or data.startswith("admin_set_content:") or data.startswith("admin_set_destinations:") or data.startswith("admin_toggle_slot:") or data.startswith("admin_slot_stats") or data == "admin_slots_refresh" or data == "admin_slots" or data.startswith("admin_category:") or data.startswith("admin_toggle_dest:") or data.startswith("admin_select_category:") or data.startswith("admin_clear_category:") or data.startswith("admin_select_all:") or data.startswith("admin_clear_all:") or data.startswith("admin_save_destinations:") or data.startswith("admin_delete_slot:") or data.startswith("admin_slot_analytics:") or data.startswith("admin_content_template:") or data.startswith("admin_clear_content:") or data.startswith("admin_quick_post_send") or data.startswith("admin_quick_post_template") or data == "admin_menu" or data.startswith("admin_detailed_analytics") or data.startswith("admin_export_stats") or data == "admin_clear_all_content" or data == "admin_clear_all_destinations" or data == "admin_purge_all_slots" or data == "admin_confirm_purge_all_slots":
                if ADMIN_SLOT_COMMANDS_AVAILABLE:
                    try:
                        from commands import admin_slot_commands
                        await admin_slot_commands.handle_admin_slot_callback(update, context)
                    except Exception as e:
                        logger.error(f"Error in admin slot callback: {e}")
                        await query.answer("Error processing admin slot action")
                else:
                    await query.answer("Admin slot features not available")
            elif data == "suggestions_menu":
                logger.info("Suggestions menu button clicked")
                if SUGGESTIONS_AVAILABLE:
                    logger.info("Suggestions system available, calling show_suggestions_menu")
                    try:
                        await show_suggestions_menu(update, context)
                        logger.info("show_suggestions_menu completed successfully")
                    except Exception as e:
                        logger.error(f"Error in show_suggestions_menu: {e}")
                        await query.answer("Error loading suggestions menu")
                else:
                    logger.warning("Suggestions system not available")
                    await query.answer("Suggestions feature not available")
            elif data in ["submit_suggestion", "my_suggestions", "suggestion_stats", "cancel_suggestions"]:
                logger.info(f"Suggestion callback triggered: {data}")
                if SUGGESTIONS_AVAILABLE:
                    try:
                        from commands.suggestion_commands import handle_suggestion_callback
                        await handle_suggestion_callback(update, context)
                        logger.info(f"Suggestion callback {data} completed successfully")
                    except Exception as e:
                        logger.error(f"Error in suggestion callback {data}: {e}")
                        await query.answer("Error processing suggestion request")
                else:
                    logger.warning("Suggestions system not available for callback")
                    await query.answer("Suggestions feature not available")
            else:
                await query.answer("This feature is coming soon!")
                logger.warning(f"Unknown callback data: {data}")
                
        except Exception as e:
            logger.error(f"Error in handle_callback: {e}")
            try:
                await update.callback_query.answer("An error occurred. Please try again.")
            except:
                pass
    
    async def _handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle admin-specific callbacks.
        
        Args:
            update: Telegram update object
            context: Bot context
            data: Callback data string
            
        Returns:
            None
        """
        try:
            if not data or ":" not in data:
                logger.error("Invalid admin callback data")
                await update.callback_query.answer("Invalid admin action")
                return
                
            action = data.split(":")[1]
            
            # Route admin actions
            if action == "restart_posting":
                await admin_commands.restart_posting_service(update, context)
            elif action == "pause_posting":
                await admin_commands.pause_posting_service(update, context)
            elif action == "detailed_stats":
                await admin_commands.posting_service_status(update, context)
            elif action == "service_config":
                await update.callback_query.answer("Service configuration coming soon!")
            elif (
                action.startswith("edit_group_cat") or
                action.startswith("set_group_cat") or
                action.startswith("edit_group_cat_custom") or
                action.startswith("remove_group") or
                action.startswith("purge_menu") or
                action.startswith("purge_category") or
                action.startswith("confirm_purge_category") or
                action.startswith("purge_group") or
                action == "purge_all_groups" or
                action == "confirm_purge_all" or
                action == "back_to_groups" or
                action == "add_to_category_menu" or
                action.startswith("add_to_category") or
                action.startswith("list_cat") or
                action.startswith("show_admin_all") or
                action.startswith("delete_user")
            ):
                await admin_commands.handle_admin_callback(update, context, action, data.split(":"))
            else:
                logger.warning(f"Unknown admin action: {action}")
                await update.callback_query.answer("Unknown admin action")
                
        except Exception as e:
            logger.error(f"Error in admin callback: {e}")
            await update.callback_query.answer("Admin action failed")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in bot operations.
        
        Args:
            update: Telegram update object (may be None)
            context: Bot context with error information
            
        Returns:
            None
        """
        try:
            error = context.error
            logger.error(f"Exception while handling an update: {error}", exc_info=error)
            
            # Handle specific error types
            if hasattr(context, 'error') and 'timeout' in str(error).lower():
                logger.warning("Timeout detected, continuing...")
            elif hasattr(context, 'error') and 'unauthorized' in str(error).lower():
                logger.error("Bot token unauthorized - check configuration")
            elif hasattr(context, 'error') and 'forbidden' in str(error).lower():
                logger.error("Bot forbidden - check permissions")
            else:
                logger.error(f"Unhandled error: {error}")
                
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            
    async def _rate_limit_check(self, user_id: int) -> bool:
        """Simple rate limiting to prevent spam."""
        current_time = datetime.now().timestamp()
        
        if not hasattr(self, '_user_last_command'):
            self._user_last_command = {}
            
        if user_id in self._user_last_command:
            time_diff = current_time - self._user_last_command[user_id]
            if time_diff < 1.0:  # 1 second between commands
                return False
                
        self._user_last_command[user_id] = current_time
        return True

    async def post_init(self, app: Application):
        logger.info("Initializing bot services...")
        try:
            await asyncio.wait_for(self.db.initialize(), timeout=30.0)
            
            # Check if external scheduler is running (disable internal components)
            disable_internal = os.getenv('DISABLE_INTERNAL_POSTING_SERVICE', '0') == '1'
            
            if disable_internal:
                logger.info("External scheduler detected - skipping internal worker/posting initialization")
            else:
                # Initialize worker manager if available
                if self.worker_manager:
                    await asyncio.wait_for(self.worker_manager.initialize_workers(), timeout=30.0)
                    logger.info("Worker manager initialized successfully!")
                
                # Initialize payment processor if available
                if self.payment_processor:
                    await asyncio.wait_for(self.payment_processor.initialize(), timeout=30.0)
                    logger.info("Payment processor initialized successfully!")
                
                # Initialize and start posting service if available and not disabled
                if self.posting_service:
                    await asyncio.wait_for(self.posting_service.initialize(), timeout=30.0)
                    logger.info("Posting service initialized successfully!")
                    
                    # Start posting service as background task
                    try:
                        asyncio.create_task(self.posting_service.start_service())
                        logger.info("Posting service started as background task!")
                    except Exception as e:
                        logger.error(f"Failed to start posting service: {e}")
                
                # Start notification scheduler if available
                if self.notification_scheduler:
                    try:
                        asyncio.create_task(self.notification_scheduler.start())
                        logger.info("Notification scheduler started as background task!")
                    except Exception as e:
                        logger.error(f"Failed to start notification scheduler: {e}")
                
                # Start price update service if available
                if self.price_service:
                    try:
                        asyncio.create_task(self.price_service.start())
                        logger.info("Price update service started as background task!")
                    except Exception as e:
                        logger.error(f"Failed to start price update service: {e}")
            
            logger.info("Bot initialization complete!")
        except asyncio.TimeoutError:
            logger.error("Database initialization timed out!")
            raise
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def shutdown(self, app: Application):
        logger.info("Shutting down bot...")
        try:
            # Check if external scheduler is running
            disable_internal = os.getenv('DISABLE_INTERNAL_POSTING_SERVICE', '0') == '1'
            
            if not disable_internal:
                # Close worker connections if available
                if self.worker_manager:
                    try:
                        await asyncio.wait_for(self.worker_manager.close_all_workers(), timeout=10.0)
                        logger.info("Worker manager closed successfully!")
                    except Exception as e:
                        logger.warning(f"Error closing worker manager: {e}")
                
                # Close payment processor if available
                if self.payment_processor:
                    try:
                        await asyncio.wait_for(self.payment_processor.close(), timeout=10.0)
                        logger.info("Payment processor closed successfully!")
                    except Exception as e:
                        logger.warning(f"Error closing payment processor: {e}")
                
                # Stop posting service if available
                if self.posting_service:
                    try:
                        # Properly stop the async posting service
                        await asyncio.wait_for(self.posting_service.stop_service(), timeout=10.0)
                        logger.info("Posting service stopped successfully!")
                    except Exception as e:
                        logger.warning(f"Error stopping posting service: {e}")
                
                # Stop price update service if available
                if self.price_service:
                    try:
                        await asyncio.wait_for(self.price_service.stop(), timeout=10.0)
                        logger.info("Price update service stopped successfully!")
                    except Exception as e:
                        logger.warning(f"Error stopping price update service: {e}")
            else:
                logger.info("External scheduler mode - skipping internal component shutdown")
            
            await asyncio.wait_for(self.db.close(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Database close timed out, forcing close...")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def run(self):
        """Run the bot."""
        lock_file = "bot.lock"
        if os.path.exists(lock_file):
            logger.error("Lock file exists. Another instance may be running. Exiting.")
            return
        try:
            # Remove stale lock if process is not running
            if os.path.exists(lock_file):
                try:
                    with open(lock_file, 'r') as f:
                        pid_str = f.read().strip()
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid != os.getpid():
                            try:
                                os.kill(pid, 0)
                                logger.error("Another instance appears to be running. Exiting.")
                                return
                            except OSError:
                                logger.warning("Stale lock detected. Removing.")
                                os.remove(lock_file)
                except Exception:
                    logger.warning("Could not verify existing lock. Removing to proceed.")
                    try: os.remove(lock_file)
                    except Exception: pass

            with open(lock_file, "w") as f: f.write(str(os.getpid()))
            self.setup_handlers()
            self.app.post_init = self.post_init
            self.app.post_shutdown = self.shutdown
            logger.info(f"Starting bot...")
            # Add timeout and error handling for polling
            self.app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down gracefully...")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
        finally:
            if os.path.exists(lock_file): 
                os.remove(lock_file)
                logger.info("Lock file removed. Bot shut down cleanly.")

if __name__ == '__main__':
    bot = AutoFarmingBot()
    bot.run()