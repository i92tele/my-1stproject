#!/usr/bin/env python3
"""
Suggestion Commands Module
Handles user suggestions with proper state management and JSON storage

Features:
- InlineKeyboardButton and InlineKeyboardMarkup for suggestions button
- CallbackQueryHandler for button clicks
- ConversationHandler for text collection
- MessageHandler with Filters.TEXT for suggestion input
- JSON file operations with proper file locking
- User ID, username, and chat ID capture
- Timestamp formatting with datetime
- Input validation (length limits, spam prevention)
"""

import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    CommandHandler,
    filters
)

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_SUGGESTION = 1

# File paths
SUGGESTIONS_FILE = "suggestions.json"
SUGGESTIONS_LOCK = threading.Lock()

# Configuration
MAX_SUGGESTION_LENGTH = 1000
MIN_SUGGESTION_LENGTH = 10
MAX_SUGGESTIONS_PER_USER = 5
SUGGESTION_COOLDOWN_HOURS = 24

class SuggestionManager:
    """Manages suggestion storage and retrieval with thread-safe operations."""
    
    def __init__(self, file_path: str = SUGGESTIONS_FILE):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the suggestions file exists with proper structure."""
        with SUGGESTIONS_LOCK:
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {
                    "suggestions": [],
                    "user_suggestions": {},
                    "metadata": {
                        "total_suggestions": 0,
                        "last_updated": datetime.now().isoformat()
                    }
                }
                self._save_data(data)
    
    def _save_data(self, data: Dict[str, Any]):
        """Save data to JSON file with proper error handling."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving suggestions data: {e}")
            raise
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file with proper error handling."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading suggestions data: {e}")
            return {
                "suggestions": [],
                "user_suggestions": {},
                "metadata": {
                    "total_suggestions": 0,
                    "last_updated": datetime.now().isoformat()
                }
            }
    
    def add_suggestion(self, user_id: int, username: str, chat_id: int, suggestion_text: str) -> bool:
        """Add a new suggestion with proper validation and storage."""
        with SUGGESTIONS_LOCK:
            data = self._load_data()
            
            # Validate suggestion length
            if len(suggestion_text) < MIN_SUGGESTION_LENGTH:
                raise ValueError(f"Suggestion too short. Minimum {MIN_SUGGESTION_LENGTH} characters required.")
            
            if len(suggestion_text) > MAX_SUGGESTION_LENGTH:
                raise ValueError(f"Suggestion too long. Maximum {MAX_SUGGESTION_LENGTH} characters allowed.")
            
            # Check user suggestion limit
            user_suggestions = data["user_suggestions"].get(str(user_id), [])
            if len(user_suggestions) >= MAX_SUGGESTIONS_PER_USER:
                raise ValueError(f"You have reached the maximum limit of {MAX_SUGGESTIONS_PER_USER} suggestions.")
            
            # Check cooldown
            current_time = datetime.now()
            if user_suggestions:
                last_suggestion_time = datetime.fromisoformat(user_suggestions[-1]["timestamp"])
                time_diff = current_time - last_suggestion_time
                if time_diff.total_seconds() < SUGGESTION_COOLDOWN_HOURS * 3600:
                    hours_remaining = SUGGESTION_COOLDOWN_HOURS - (time_diff.total_seconds() / 3600)
                    raise ValueError(f"Please wait {hours_remaining:.1f} hours before submitting another suggestion.")
            
            # Create suggestion object
            suggestion = {
                "id": data["metadata"]["total_suggestions"] + 1,
                "user_id": user_id,
                "username": username,
                "chat_id": chat_id,
                "suggestion": suggestion_text,
                "timestamp": current_time.isoformat(),
                "status": "pending"
            }
            
            # Add to suggestions list
            data["suggestions"].append(suggestion)
            
            # Update user suggestions
            if str(user_id) not in data["user_suggestions"]:
                data["user_suggestions"][str(user_id)] = []
            data["user_suggestions"][str(user_id)].append(suggestion)
            
            # Update metadata
            data["metadata"]["total_suggestions"] += 1
            data["metadata"]["last_updated"] = current_time.isoformat()
            
            # Save data
            self._save_data(data)
            
            logger.info(f"Suggestion added by user {user_id} ({username})")
            return True
    
    def get_user_suggestions(self, user_id: int) -> list:
        """Get all suggestions by a specific user."""
        with SUGGESTIONS_LOCK:
            data = self._load_data()
            return data["user_suggestions"].get(str(user_id), [])
    
    def get_all_suggestions(self, limit: Optional[int] = None) -> list:
        """Get all suggestions with optional limit."""
        with SUGGESTIONS_LOCK:
            data = self._load_data()
            suggestions = data["suggestions"]
            if limit:
                suggestions = suggestions[-limit:]
            return suggestions
    
    def get_suggestion_stats(self) -> Dict[str, Any]:
        """Get suggestion statistics."""
        with SUGGESTIONS_LOCK:
            data = self._load_data()
            return {
                "total_suggestions": data["metadata"]["total_suggestions"],
                "unique_users": len(data["user_suggestions"]),
                "last_updated": data["metadata"]["last_updated"]
            }

# Global suggestion manager instance
suggestion_manager = SuggestionManager()

async def show_suggestions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the suggestions menu with inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("💡 Submit Suggestion", callback_data="submit_suggestion"),
            InlineKeyboardButton("📋 My Suggestions", callback_data="my_suggestions")
        ],
        [
            InlineKeyboardButton("📊 Suggestion Stats", callback_data="suggestion_stats"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_suggestions")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "💡 **Suggestions Menu**\n\n"
        "Welcome to the suggestions system! Here you can:\n"
        "• Submit new suggestions for bot improvements\n"
        "• View your previous suggestions\n"
        "• Check suggestion statistics\n\n"
        "Please select an option:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle suggestion button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "submit_suggestion":
        await start_suggestion_input(update, context)
    elif query.data == "my_suggestions":
        await show_user_suggestions(update, context)
    elif query.data == "suggestion_stats":
        await show_suggestion_stats(update, context)
    elif query.data == "cancel_suggestions":
        await cancel_suggestions(update, context)
    elif query.data == "suggestions_menu":
        await show_suggestions_menu(update, context)

async def start_suggestion_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the suggestion input conversation."""
    query = update.callback_query
    
    text = (
        "💡 **Submit a Suggestion**\n\n"
        f"Please type your suggestion below.\n"
        f"**Requirements:**\n"
        f"• Minimum {MIN_SUGGESTION_LENGTH} characters\n"
        f"• Maximum {MAX_SUGGESTION_LENGTH} characters\n"
        f"• Be specific and constructive\n\n"
        f"Type /cancel to cancel."
    )
    
    await query.edit_message_text(
        text=text,
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_SUGGESTION

async def handle_suggestion_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle suggestion text input with validation."""
    user = update.effective_user
    message = update.message
    
    try:
        # Validate input
        suggestion_text = message.text.strip()
        
        if len(suggestion_text) < MIN_SUGGESTION_LENGTH:
            await message.reply_text(
                f"❌ **Suggestion too short!**\n\n"
                f"Your suggestion has {len(suggestion_text)} characters.\n"
                f"Minimum required: {MIN_SUGGESTION_LENGTH} characters.\n\n"
                f"Please try again or type /cancel to cancel.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_SUGGESTION
        
        if len(suggestion_text) > MAX_SUGGESTION_LENGTH:
            await message.reply_text(
                f"❌ **Suggestion too long!**\n\n"
                f"Your suggestion has {len(suggestion_text)} characters.\n"
                f"Maximum allowed: {MAX_SUGGESTION_LENGTH} characters.\n\n"
                f"Please shorten your suggestion or type /cancel to cancel.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_SUGGESTION
        
        # Add suggestion to storage
        success = suggestion_manager.add_suggestion(
            user_id=user.id,
            username=user.username or user.first_name,
            chat_id=message.chat_id,
            suggestion_text=suggestion_text
        )
        
        if success:
            # Success message
            keyboard = [
                [
                    InlineKeyboardButton("💡 Submit Another", callback_data="submit_suggestion"),
                    InlineKeyboardButton("📋 View My Suggestions", callback_data="my_suggestions")
                ],
                [
                    InlineKeyboardButton("🏠 Back to Menu", callback_data="suggestions_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                "✅ **Suggestion Submitted Successfully!**\n\n"
                f"**Your suggestion:**\n{suggestion_text[:100]}{'...' if len(suggestion_text) > 100 else ''}\n\n"
                "Thank you for your feedback! We'll review it carefully.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
        
    except ValueError as e:
        await message.reply_text(
            f"❌ **Error:** {str(e)}\n\n"
            "Please try again or type /cancel to cancel.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_SUGGESTION
        
    except Exception as e:
        logger.error(f"Error processing suggestion: {e}")
        await message.reply_text(
            "❌ **An error occurred while processing your suggestion.**\n\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def show_user_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's previous suggestions."""
    query = update.callback_query
    user = query.from_user
    
    try:
        suggestions = suggestion_manager.get_user_suggestions(user.id)
        
        if not suggestions:
            keyboard = [
                [
                    InlineKeyboardButton("💡 Submit First Suggestion", callback_data="submit_suggestion"),
                    InlineKeyboardButton("🏠 Back to Menu", callback_data="suggestions_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📋 **My Suggestions**\n\n"
                "You haven't submitted any suggestions yet.\n"
                "Be the first to share your ideas!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Format suggestions
        text = f"📋 **My Suggestions** ({len(suggestions)} total)\n\n"
        
        for i, suggestion in enumerate(suggestions[-5:], 1):  # Show last 5
            timestamp = datetime.fromisoformat(suggestion["timestamp"]).strftime("%Y-%m-%d %H:%M")
            status_emoji = "⏳" if suggestion["status"] == "pending" else "✅" if suggestion["status"] == "approved" else "❌"
            
            text += f"**{i}. {status_emoji} {suggestion['status'].title()}**\n"
            text += f"📅 {timestamp}\n"
            text += f"💬 {suggestion['suggestion'][:100]}{'...' if len(suggestion['suggestion']) > 100 else ''}\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("💡 Submit New Suggestion", callback_data="submit_suggestion"),
                InlineKeyboardButton("📊 View Stats", callback_data="suggestion_stats")
            ],
            [
                InlineKeyboardButton("🏠 Back to Menu", callback_data="suggestions_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing user suggestions: {e}")
        await query.edit_message_text(
            "❌ **Error loading your suggestions.**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def show_suggestion_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show suggestion statistics."""
    query = update.callback_query
    
    try:
        stats = suggestion_manager.get_suggestion_stats()
        last_updated = datetime.fromisoformat(stats["last_updated"]).strftime("%Y-%m-%d %H:%M")
        
        text = (
            "📊 **Suggestion Statistics**\n\n"
            f"📈 **Total Suggestions:** {stats['total_suggestions']}\n"
            f"👥 **Unique Users:** {stats['unique_users']}\n"
            f"🕐 **Last Updated:** {last_updated}\n\n"
            f"📋 **Limits:**\n"
            f"• Max suggestions per user: {MAX_SUGGESTIONS_PER_USER}\n"
            f"• Cooldown period: {SUGGESTION_COOLDOWN_HOURS} hours\n"
            f"• Min length: {MIN_SUGGESTION_LENGTH} characters\n"
            f"• Max length: {MAX_SUGGESTION_LENGTH} characters"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("💡 Submit Suggestion", callback_data="submit_suggestion"),
                InlineKeyboardButton("📋 My Suggestions", callback_data="my_suggestions")
            ],
            [
                InlineKeyboardButton("🏠 Back to Menu", callback_data="suggestions_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing suggestion stats: {e}")
        await query.edit_message_text(
            "❌ **Error loading statistics.**\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )

async def cancel_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel suggestions and return to main menu."""
    query = update.callback_query
    
    await query.edit_message_text(
        "❌ **Suggestions cancelled.**\n\n"
        "You can access suggestions again from the main menu.",
        parse_mode='Markdown'
    )

async def cancel_suggestion_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel suggestion input conversation."""
    await update.message.reply_text(
        "❌ **Suggestion cancelled.**\n\n"
        "You can submit a new suggestion anytime from the suggestions menu.",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# Admin commands for managing suggestions
async def admin_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all suggestions."""
    # Check if user is admin
    try:
        from commands.admin_commands import check_admin
        if not await check_admin(update, context):
            await update.message.reply_text("❌ Admin access required.")
            return
    except ImportError:
        await update.message.reply_text("❌ Admin check not available.")
        return
    
    try:
        suggestions = suggestion_manager.get_all_suggestions(limit=20)
        
        if not suggestions:
            await update.message.reply_text("📋 No suggestions found.")
            return
        
        text = f"📋 **All Suggestions** (Last {len(suggestions)})\n\n"
        
        for suggestion in suggestions:
            timestamp = datetime.fromisoformat(suggestion["timestamp"]).strftime("%Y-%m-%d %H:%M")
            status_emoji = "⏳" if suggestion["status"] == "pending" else "✅" if suggestion["status"] == "approved" else "❌"
            
            text += f"**ID {suggestion['id']}:** {status_emoji} {suggestion['status'].title()}\n"
            text += f"👤 @{suggestion['username']} (ID: {suggestion['user_id']})\n"
            text += f"📅 {timestamp}\n"
            text += f"💬 {suggestion['suggestion'][:150]}{'...' if len(suggestion['suggestion']) > 150 else ''}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_suggestions: {e}")
        await update.message.reply_text("❌ Error loading suggestions.")

def get_suggestion_handlers():
    """Get all suggestion-related handlers for bot registration."""
    
    # Main suggestions command
    suggestion_command = CommandHandler("suggestions", show_suggestions_menu)
    
    # Callback query handler for suggestion buttons (excluding submit_suggestion which is handled by conversation)
    callback_handler = CallbackQueryHandler(handle_suggestion_callback, pattern="^(my_suggestions|suggestion_stats|cancel_suggestions|suggestions_menu)$")
    
    # Conversation handler for suggestion input
    suggestion_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_suggestion_input, pattern="^submit_suggestion$")],
        states={
            WAITING_FOR_SUGGESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_suggestion_text),
                CommandHandler("cancel", cancel_suggestion_input)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_suggestion_input)],
        name="suggestion_conversation",
        persistent=False,
        per_message=False
    )
    
    # Admin command
    admin_command = CommandHandler("admin_suggestions", admin_suggestions)
    
    return [
        suggestion_command,
        callback_handler,
        suggestion_conversation,
        admin_command
    ]

# Export the suggestion manager for external use
__all__ = ['SuggestionManager', 'suggestion_manager', 'get_suggestion_handlers']
