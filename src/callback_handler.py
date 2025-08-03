import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .core_systems import safe_rate_limit, safe_error_handling
from .ui_manager import get_ui_manager

class CallbackHandler:
    """Handle all callback queries for UI interactions."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @safe_error_handling
    @safe_rate_limit("callback_query")
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main callback handler that routes to appropriate functions."""
        query = update.callback_query
        await query.answer()  # Always answer callback query
        
        data = query.data
        self.logger.debug(f"Received callback: {data}")
        
        # Route to appropriate handler
        if data.startswith("menu_"):
            await self._handle_menu_navigation(update, context, data)
        elif data.startswith("subscribe_"):
            await self._handle_subscription(update, context, data)
        elif data.startswith("manage_slot_"):
            await self._handle_slot_management(update, context, data)
        elif data.startswith("buy_slot"):
            await self._handle_buy_slot(update, context)
        elif data.startswith("settings_"):
            await self._handle_settings(update, context, data)
        elif data.startswith("help_"):
            await self._handle_help(update, context, data)
        else:
            await self._handle_unknown_callback(update, context, data)
    
    async def _handle_menu_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle menu navigation callbacks."""
        ui_manager = get_ui_manager()
        if not ui_manager:
            await self._send_fallback_message(update, context, "UI system not available")
            return
        
        menu_name = data.replace("menu_", "")
        
        menu_handlers = {
            "main": ui_manager.show_main_menu,
            "subscribe": ui_manager.show_subscribe_menu,
            "status": ui_manager.show_status_menu,
            "slots": ui_manager.show_slots_menu,
            "settings": ui_manager.show_settings_menu,
            "help": ui_manager.show_help_menu
        }
        
        handler = menu_handlers.get(menu_name)
        if handler:
            await handler(update, context)
        else:
            await self._send_fallback_message(update, context, f"Menu '{menu_name}' not found")
    
    async def _handle_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle subscription-related callbacks."""
        plan = data.replace("subscribe_", "")
        
        if plan in ["basic", "pro", "enterprise"]:
            await self._process_subscription(update, context, plan)
        else:
            await self._send_fallback_message(update, context, f"Unknown plan: {plan}")
    
    async def _process_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str):
        """Process subscription selection."""
        user_id = update.effective_user.id
        
        # Plan configurations
        plan_configs = {
            "basic": {"price": 15, "slots": 1, "duration": 30},
            "pro": {"price": 30, "slots": 3, "duration": 30},
            "enterprise": {"price": 50, "slots": 5, "duration": 30}
        }
        
        config = plan_configs.get(plan)
        if not config:
            await self._send_fallback_message(update, context, f"Invalid plan: {plan}")
            return
        
        # Create payment
        payment_handler = context.bot_data.get('payment_timeout_handler')
        if payment_handler:
            payment_data = await payment_handler.create_payment_with_timeout(
                user_id=user_id,
                amount=config["price"],
                currency="USD",
                timeout_minutes=30
            )
            
            # Show payment instructions
            keyboard = [
                [InlineKeyboardButton("💳 Pay Now", callback_data=f"pay_{payment_data['payment_id']}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_subscribe")]
            ]
            
            text = (
                f"💎 **{plan.title()} Plan - ${config['price']}/month**\n\n"
                f"**Features:**\n"
                f"• {config['slots']} ad slot(s)\n"
                f"• 10 destinations per slot\n"
                f"• {config['duration']} days duration\n\n"
                f"**Payment ID:** `{payment_data['payment_id']}`\n"
                f"**Amount:** ${config['price']}\n\n"
                f"Click 'Pay Now' to proceed with payment."
            )
            
            await self._edit_message(update, context, text, keyboard)
        else:
            await self._send_fallback_message(update, context, "Payment system not available")
    
    async def _handle_slot_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle slot management callbacks."""
        parts = data.split("_")
        if len(parts) < 3:
            await self._send_fallback_message(update, context, "Invalid slot management callback")
            return
        
        action = parts[1]
        slot_id = int(parts[2])
        
        if action == "set_content":
            await self._handle_set_content(update, context, slot_id)
        elif action == "add_destinations":
            await self._handle_add_destinations(update, context, slot_id)
        elif action == "view_destinations":
            await self._handle_view_destinations(update, context, slot_id)
        elif action == "toggle_active":
            await self._handle_toggle_active(update, context, slot_id)
        else:
            await self._send_fallback_message(update, context, f"Unknown slot action: {action}")
    
    async def _handle_set_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: int):
        """Handle set content action."""
        keyboard = [
            [InlineKeyboardButton("📝 Send Content", callback_data=f"send_content_{slot_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
        ]
        
        text = (
            f"📝 **Set Content for Slot**\n\n"
            f"Send the message you want to post to your destinations.\n\n"
            f"You can send:\n"
            f"• Text message\n"
            f"• Photo with caption\n"
            f"• Video with caption\n"
            f"• Document with caption\n\n"
            f"Click 'Send Content' to start."
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _handle_add_destinations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: int):
        """Handle add destinations action."""
        keyboard = [
            [InlineKeyboardButton("📤 Forward Message", callback_data=f"forward_dest_{slot_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
        ]
        
        text = (
            f"🎯 **Add Destinations to Slot**\n\n"
            f"Forward a message from the group/channel where you want to post.\n\n"
            f"Make sure the bot is added to that group/channel first.\n\n"
            f"Click 'Forward Message' to start."
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _handle_view_destinations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: int):
        """Handle view destinations action."""
        db = context.bot_data['db']
        destinations = await db.get_slot_destinations(slot_id)
        
        if destinations:
            text = f"📋 **Destinations for Slot**\n\n"
            for i, dest in enumerate(destinations, 1):
                name = dest.get('alias') or dest['destination_name']
                text += f"{i}. {name}\n"
            
            keyboard = [
                [InlineKeyboardButton("🗑️ Remove Destination", callback_data=f"remove_dest_{slot_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
            ]
        else:
            text = "📋 **No destinations set for this slot.**\n\nAdd destinations to start posting."
            keyboard = [
                [InlineKeyboardButton("➕ Add Destinations", callback_data=f"add_destinations_{slot_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
            ]
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _handle_toggle_active(self, update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: int):
        """Handle toggle active action."""
        db = context.bot_data['db']
        
        # Get current slot status
        slots = await db.get_user_slots(update.effective_user.id)
        slot = next((s for s in slots if s['id'] == slot_id), None)
        
        if not slot:
            await self._send_fallback_message(update, context, "Slot not found")
            return
        
        # Toggle status
        if slot['is_active']:
            success = await db.deactivate_slot(slot_id)
            new_status = "❌ Inactive"
        else:
            success = await db.activate_slot(slot_id)
            new_status = "✅ Active"
        
        if success:
            keyboard = [
                [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
            ]
            
            text = (
                f"⚡ **Slot Status Updated**\n\n"
                f"Slot is now: **{new_status}**\n\n"
                f"Active slots will automatically post to their destinations."
            )
            
            await self._edit_message(update, context, text, keyboard)
        else:
            await self._send_fallback_message(update, context, "Failed to update slot status")
    
    async def _handle_buy_slot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle buy slot action."""
        user_id = update.effective_user.id
        db = context.bot_data['db']
        
        # Check subscription
        subscription = await db.get_user_subscription(user_id)
        if not subscription or not subscription['is_active']:
            keyboard = [
                [InlineKeyboardButton("💎 Get Subscription", callback_data="menu_subscribe")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
            ]
            
            text = (
                "❌ **Subscription Required**\n\n"
                "You need an active subscription to buy ad slots.\n\n"
                "Please subscribe first."
            )
            
            await self._edit_message(update, context, text, keyboard)
            return
        
        # Create new slot
        slots = await db.get_user_slots(user_id)
        new_slot_number = len(slots) + 1
        slot_id = await db.create_ad_slot(user_id, new_slot_number)
        
        if slot_id:
            keyboard = [
                [InlineKeyboardButton("📝 Set Content", callback_data=f"set_content_{slot_id}")],
                [InlineKeyboardButton("🎯 Add Destinations", callback_data=f"add_destinations_{slot_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
            ]
            
            text = (
                f"✅ **Slot {new_slot_number} Created!**\n\n"
                f"Your new ad slot is ready to configure.\n\n"
                f"Next steps:\n"
                f"1. Set content for your ads\n"
                f"2. Add destinations (groups/channels)\n"
                f"3. Activate the slot to start posting"
            )
            
            await self._edit_message(update, context, text, keyboard)
        else:
            await self._send_fallback_message(update, context, "Failed to create ad slot")
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle settings callbacks."""
        setting = data.replace("settings_", "")
        
        if setting == "notifications":
            await self._show_notifications_settings(update, context)
        elif setting == "language":
            await self._show_language_settings(update, context)
        elif setting == "privacy":
            await self._show_privacy_settings(update, context)
        else:
            await self._send_fallback_message(update, context, f"Unknown setting: {setting}")
    
    async def _show_notifications_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show notifications settings."""
        keyboard = [
            [InlineKeyboardButton("🔔 Enable All", callback_data="notif_enable_all")],
            [InlineKeyboardButton("🔕 Disable All", callback_data="notif_disable_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]
        ]
        
        text = (
            "🔔 **Notification Settings**\n\n"
            "Configure which notifications you want to receive:\n\n"
            "• Payment confirmations\n"
            "• Ad posting status\n"
            "• Subscription reminders\n"
            "• System updates"
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _show_language_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show language settings."""
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")],
            [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]
        ]
        
        text = (
            "🌐 **Language Settings**\n\n"
            "Choose your preferred language:"
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _show_privacy_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show privacy settings."""
        keyboard = [
            [InlineKeyboardButton("🔒 High Privacy", callback_data="privacy_high")],
            [InlineKeyboardButton("🔓 Standard", callback_data="privacy_standard")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_settings")]
        ]
        
        text = (
            "🔒 **Privacy Settings**\n\n"
            "Configure your privacy preferences:\n\n"
            "• Data collection\n"
            "• Analytics sharing\n"
            "• Message storage"
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle help callbacks."""
        help_topic = data.replace("help_", "")
        
        if help_topic == "how_it_works":
            await self._show_how_it_works(update, context)
        elif help_topic == "faq":
            await self._show_faq(update, context)
        elif help_topic == "support":
            await self._show_support(update, context)
        else:
            await self._send_fallback_message(update, context, f"Unknown help topic: {help_topic}")
    
    async def _show_how_it_works(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show how it works help."""
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="menu_help")]
        ]
        
        text = (
            "📖 **How It Works**\n\n"
            "1. **Subscribe** - Choose a plan that fits your needs\n"
            "2. **Create Slots** - Each slot can have 10 destinations\n"
            "3. **Set Content** - Add your ad message or media\n"
            "4. **Add Destinations** - Choose groups/channels to post to\n"
            "5. **Activate** - Turn on your slot to start posting\n\n"
            "The bot will automatically post your content to all destinations at regular intervals."
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show FAQ help."""
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="menu_help")]
        ]
        
        text = (
            "❓ **Frequently Asked Questions**\n\n"
            "**Q: How many groups can I post to?**\n"
            "A: Each slot supports up to 10 destinations.\n\n"
            "**Q: How often does it post?**\n"
            "A: By default, every 60 minutes.\n\n"
            "**Q: Can I use my own content?**\n"
            "A: Yes, you can set custom text, photos, or videos.\n\n"
            "**Q: What if the bot gets banned?**\n"
            "A: We automatically rotate workers to avoid bans."
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _show_support(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show support information."""
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_help")]
        ]
        
        text = (
            "📞 **Support**\n\n"
            "Need help? We're here to assist you!\n\n"
            "**Contact Methods:**\n"
            "• Telegram: @support_username\n"
            "• Email: support@example.com\n"
            "• Response time: Within 24 hours\n\n"
            "**Before contacting:**\n"
            "• Check the FAQ section\n"
            "• Try restarting the bot\n"
            "• Ensure your subscription is active"
        )
        
        await self._edit_message(update, context, text, keyboard)
    
    async def _handle_unknown_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle unknown callbacks."""
        self.logger.warning(f"Unknown callback data: {data}")
        await self._send_fallback_message(update, context, "Unknown action. Please try again.")
    
    async def _edit_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, keyboard: list):
        """Edit the callback message with new content."""
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Error editing message: {e}")
            # Fallback to simple text
            fallback_text = text.replace('*', '').replace('_', '')
            await update.callback_query.edit_message_text(fallback_text)
    
    async def _send_fallback_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
        """Send a fallback message when something goes wrong."""
        try:
            await update.callback_query.edit_message_text(f"❌ {message}")
        except Exception as e:
            self.logger.error(f"Error sending fallback message: {e}")

# Global callback handler instance
callback_handler = None

def initialize_callback_handler(logger: logging.Logger):
    """Initialize the global callback handler."""
    global callback_handler
    callback_handler = CallbackHandler(logger)
    return callback_handler

def get_callback_handler() -> Optional[CallbackHandler]:
    """Get the global callback handler instance."""
    return callback_handler 