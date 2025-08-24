import logging
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from src.core_systems import safe_rate_limit, safe_error_handling

class UIManager:
    """Production-ready UI manager for button-based menus."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.menu_stack: Dict[int, List[str]] = {}  # Track user's menu navigation
        self.menu_data: Dict[int, Dict[str, Any]] = {}  # Store menu-specific data
        
    def _get_user_stack(self, user_id: int) -> List[str]:
        """Get user's menu navigation stack."""
        if user_id not in self.menu_stack:
            self.menu_stack[user_id] = []
        return self.menu_stack[user_id]
    
    def _push_menu(self, user_id: int, menu_name: str):
        """Add menu to user's navigation stack."""
        stack = self._get_user_stack(user_id)
        stack.append(menu_name)
        self.logger.debug(f"User {user_id} navigated to {menu_name}")
    
    def _pop_menu(self, user_id: int) -> Optional[str]:
        """Remove and return the last menu from user's stack."""
        stack = self._get_user_stack(user_id)
        if stack:
            return stack.pop()
        return None
    
    def _get_current_menu(self, user_id: int) -> Optional[str]:
        """Get user's current menu."""
        stack = self._get_user_stack(user_id)
        return stack[-1] if stack else None
    
    def _clear_user_data(self, user_id: int):
        """Clear user's menu data."""
        if user_id in self.menu_stack:
            del self.menu_stack[user_id]
        if user_id in self.menu_data:
            del self.menu_data[user_id]
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu with all options."""
        user_id = update.effective_user.id
        self._clear_user_data(user_id)  # Reset navigation
        
        keyboard = [
            [InlineKeyboardButton("💎 View Plans", callback_data="menu_subscribe")],
            [InlineKeyboardButton("📊 My Status", callback_data="menu_status")],
            [InlineKeyboardButton("🎯 My Slots", callback_data="menu_slots")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
            [InlineKeyboardButton("❓ Help", callback_data="menu_help")]
        ]
        
        text = (
            "🚀 **Welcome to AutoFarming Bot!**\n\n"
            "I help you automate your ad posting across multiple Telegram groups.\n\n"
            "Choose an option below:"
        )
        
        self._push_menu(user_id, "main")
        await self._send_menu_message(update, context, text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_subscribe_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show subscription plans menu."""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("Basic - $15/month", callback_data="subscribe_basic")],
            [InlineKeyboardButton("Pro - $30/month", callback_data="subscribe_pro")],
            [InlineKeyboardButton("Enterprise - $50/month", callback_data="subscribe_enterprise")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ]
        
        text = (
            "💎 **Subscription Plans**\n\n"
            "**Basic Plan - $15/month**\n"
            "• 1 ad slot with 10 destinations\n"
            "• Hourly posting\n"
            "• Basic analytics\n\n"
            "**Pro Plan - $30/month**\n"
            "• 3 ad slots with 10 destinations each\n"
            "• Priority posting\n"
            "• Advanced analytics\n\n"
            "**Enterprise Plan - $50/month**\n"
            "• 5 ad slots with 10 destinations each\n"
            "• Premium support\n"
            "• Custom features\n\n"
            "Choose your plan:"
        )
        
        self._push_menu(user_id, "subscribe")
        await self._send_menu_message(update, context, text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_status_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user status menu."""
        user_id = update.effective_user.id
        
        # Get user status from database
        db = context.bot_data['db']
        subscription = await db.get_user_subscription(user_id)
        
        keyboard = []
        if subscription and subscription['is_active']:
            status_text = (
                f"📊 **Your Status**\n\n"
                f"✅ **Active Subscription**\n"
                f"📅 Expires: {subscription['expires']}\n"
                f"🎯 Plan: {subscription['tier'].title()}\n\n"
                f"Your subscription is active and ready to use!"
            )
            keyboard.append([InlineKeyboardButton("🔄 Renew", callback_data="menu_subscribe")])
        else:
            status_text = (
                "📊 **Your Status**\n\n"
                "❌ **No Active Subscription**\n\n"
                "You need a subscription to use the bot's features."
            )
            keyboard.append([InlineKeyboardButton("💎 Get Subscription", callback_data="menu_subscribe")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        
        self._push_menu(user_id, "status")
        await self._send_menu_message(update, context, status_text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_slots_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's ad slots menu."""
        user_id = update.effective_user.id
        
        # Get user's slots from database
        db = context.bot_data['db']
        slots = await db.get_user_slots(user_id)
        
        keyboard = []
        if slots:
            text = "🎯 **Your Ad Slots**\n\n"
            for i, slot in enumerate(slots, 1):
                status = "✅ Active" if slot['is_active'] else "❌ Inactive"
                destinations = len(slot.get('destinations', []))
                text += f"**Slot {i}** ({status})\n"
                text += f"• Destinations: {destinations}/10\n"
                text += f"• Content: {'Set' if slot.get('content') else 'Not set'}\n\n"
                
                keyboard.append([InlineKeyboardButton(f"Manage Slot {i}", callback_data=f"manage_slot_{slot['id']}")])
        else:
            text = (
                "🎯 **Your Ad Slots**\n\n"
                "You don't have any ad slots yet.\n"
                "Purchase a subscription to get started!"
            )
        
        keyboard.append([InlineKeyboardButton("➕ Buy New Slot", callback_data="buy_slot")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_main")])
        
        self._push_menu(user_id, "slots")
        await self._send_menu_message(update, context, text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu."""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
            [InlineKeyboardButton("🌐 Language", callback_data="settings_language")],
            [InlineKeyboardButton("🔒 Privacy", callback_data="settings_privacy")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ]
        
        text = (
            "⚙️ **Settings**\n\n"
            "Configure your bot preferences:"
        )
        
        self._push_menu(user_id, "settings")
        await self._send_menu_message(update, context, text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def show_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu."""
        user_id = update.effective_user.id
        
        keyboard = [
            [InlineKeyboardButton("📖 How It Works", callback_data="help_how_it_works")],
            [InlineKeyboardButton("❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton("📞 Support", callback_data="help_support")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_main")]
        ]
        
        text = (
            "❓ **Help & Support**\n\n"
            "Need help? Choose an option below:"
        )
        
        self._push_menu(user_id, "help")
        await self._send_menu_message(update, context, text, keyboard)
    
    @safe_error_handling
    @safe_rate_limit("ui_navigation")
    async def go_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Navigate back to previous menu."""
        user_id = update.effective_user.id
        previous_menu = self._pop_menu(user_id)
        
        if previous_menu:
            # Navigate to previous menu
            await self._navigate_to_menu(update, context, previous_menu)
        else:
            # No previous menu, go to main
            await self.show_main_menu(update, context)
    
    async def _navigate_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, menu_name: str):
        """Navigate to a specific menu."""
        menu_handlers = {
            "main": self.show_main_menu,
            "subscribe": self.show_subscribe_menu,
            "status": self.show_status_menu,
            "slots": self.show_slots_menu,
            "settings": self.show_settings_menu,
            "help": self.show_help_menu
        }
        
        handler = menu_handlers.get(menu_name)
        if handler:
            await handler(update, context)
        else:
            await self.show_main_menu(update, context)
    
    async def _send_menu_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                text: str, keyboard: List[List[InlineKeyboardButton]]):
        """Send a menu message with proper error handling."""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text, 
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        except Exception as e:
            self.logger.error(f"Error sending menu message: {e}")
            # Fallback to simple text
            fallback_text = text.replace('*', '').replace('_', '')
            if update.callback_query:
                await update.callback_query.edit_message_text(fallback_text)
            else:
                await update.message.reply_text(fallback_text)
    
    def get_user_menu_stack(self, user_id: int) -> List[str]:
        """Get user's current menu navigation stack."""
        return self._get_user_stack(user_id)
    
    def clear_user_navigation(self, user_id: int):
        """Clear user's navigation history."""
        self._clear_user_data(user_id)

# Global UI manager instance
ui_manager = None

def initialize_ui_manager(logger: logging.Logger):
    """Initialize the global UI manager."""
    global ui_manager
    ui_manager = UIManager(logger)
    return ui_manager

def get_ui_manager() -> Optional[UIManager]:
    """Get the global UI manager instance."""
    return ui_manager 