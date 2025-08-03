from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from ..decorators import rate_limit
from ..core_systems import safe_rate_limit, safe_error_handling
from ..ui_manager import get_ui_manager

@safe_error_handling
@safe_rate_limit("start_command")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show main menu."""
    user = update.effective_user
    db = context.bot_data['db']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Create or update user
    await db.create_or_update_user(
        user_id=user.id, 
        username=user.username, 
        first_name=user.first_name, 
        last_name=user.last_name
    )
    
    # Show main menu using UI manager
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_main_menu(update, context)
    else:
        # Fallback to simple welcome message
        welcome_text = f"👋 Welcome {user.first_name}!\n\nI'm a message forwarding bot. Use /help to see what I can do."
        await update.message.reply_text(welcome_text)

@safe_error_handling
@safe_rate_limit("help_command")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command - show help menu."""
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_help_menu(update, context)
    else:
        # Fallback help text
        help_text = (
            "📚 **Available Commands:**\n\n"
            "/start - Main menu\n"
            "/help - This message\n"
            "/subscribe - View plans\n"
            "/status - Check subscription\n"
            "/slots - Manage ad slots\n"
            "/settings - Bot settings\n"
            "/cancel - Cancel operation"
        )
        message = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await update.callback_query.answer()
        await message.reply_text(help_text, parse_mode='Markdown')

@safe_error_handling
@safe_rate_limit("subscribe_command")
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe command - show subscription plans."""
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_subscribe_menu(update, context)
    else:
        # Fallback subscription menu
        keyboard = [
            [InlineKeyboardButton("Basic - $15/month", callback_data="subscribe_basic")],
            [InlineKeyboardButton("Pro - $30/month", callback_data="subscribe_pro")],
            [InlineKeyboardButton("Enterprise - $50/month", callback_data="subscribe_enterprise")]
        ]
        text = "💎 **Subscription Plans**\n\nChoose a plan:"
        message = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await update.callback_query.answer()
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

@safe_error_handling
@safe_rate_limit("status_command")
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command - show user status."""
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_status_menu(update, context)
    else:
        # Fallback status display
        user_id = update.effective_user.id
        db = context.bot_data['db']
        subscription = await db.get_user_subscription(user_id)
        
        if subscription and subscription['is_active']:
            status_text = f"📊 **Your Status:**\n\n✅ Plan: **{subscription['tier'].title()}**\n📅 Expires: {subscription['expires']}"
        else:
            status_text = "📊 **Your Status:**\n\n❌ No active subscription"
        
        message = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await update.callback_query.answer()
            await message.edit_text(status_text, parse_mode='Markdown')
        else:
            await message.reply_text(status_text, parse_mode='Markdown')

@safe_error_handling
@safe_rate_limit("slots_command")
async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Slots command - show user's ad slots."""
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_slots_menu(update, context)
    else:
        # Fallback slots display
        user_id = update.effective_user.id
        db = context.bot_data['db']
        slots = await db.get_user_slots(user_id)
        
        if slots:
            text = "🎯 **Your Ad Slots:**\n\n"
            for i, slot in enumerate(slots, 1):
                status = "✅ Active" if slot['is_active'] else "❌ Inactive"
                destinations = len(slot.get('destinations', []))
                text += f"**Slot {i}** ({status})\n"
                text += f"• Destinations: {destinations}/10\n\n"
        else:
            text = "🎯 **Your Ad Slots:**\n\nYou don't have any ad slots yet."
        
        message = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await update.callback_query.answer()
            await message.edit_text(text, parse_mode='Markdown')
        else:
            await message.reply_text(text, parse_mode='Markdown')

@safe_error_handling
@safe_rate_limit("settings_command")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings command - show settings menu."""
    ui_manager = get_ui_manager()
    if ui_manager:
        await ui_manager.show_settings_menu(update, context)
    else:
        # Fallback settings menu
        keyboard = [
            [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
            [InlineKeyboardButton("🌐 Language", callback_data="settings_language")],
            [InlineKeyboardButton("🔒 Privacy", callback_data="settings_privacy")]
        ]
        text = "⚙️ **Settings**\n\nConfigure your bot preferences:"
        message = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await update.callback_query.answer()
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel command - cancel current operation."""
    context.user_data.clear()
    message_text = "Operation cancelled."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message_text)
    else:
        await update.message.reply_text(message_text)
    return ConversationHandler.END

# Conversation states for slot management
(ASK_SLOT_CONTENT, ASK_SLOT_DESTINATIONS) = range(10, 12)

@safe_error_handling
@safe_rate_limit("buy_slot_command")
async def buy_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy a new ad slot."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    # Check if user has active subscription
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await update.message.reply_text("❌ You need an active subscription to buy ad slots.")
        return
    
    # Get current slots
    slots = await db.get_user_slots(user_id)
    new_slot_number = len(slots) + 1
    
    # Create new slot
    slot_id = await db.create_ad_slot(user_id, new_slot_number)
    if slot_id:
        await update.message.reply_text(
            f"✅ Successfully created Slot {new_slot_number}!\n\n"
            "Use /manage_slot to set content and destinations."
        )
    else:
        await update.message.reply_text("❌ Failed to create ad slot. Please try again.")

@safe_error_handling
@safe_rate_limit("manage_slot_command")
async def manage_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage a specific ad slot."""
    if not context.args:
        await update.message.reply_text("Usage: /manage_slot <slot_number>")
        return
    
    try:
        slot_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid slot number.")
        return
    
    user_id = update.effective_user.id
    db = context.bot_data['db']
    slots = await db.get_user_slots(user_id)
    
    if slot_number > len(slots):
        await update.message.reply_text(f"Slot {slot_number} doesn't exist. You have {len(slots)} slots.")
        return
    
    slot = slots[slot_number - 1]
    context.user_data['managing_slot_id'] = slot['id']
    
    keyboard = [
        [InlineKeyboardButton("📝 Set Content", callback_data=f"set_content_{slot['id']}")],
        [InlineKeyboardButton("🎯 Add Destinations", callback_data=f"add_destinations_{slot['id']}")],
        [InlineKeyboardButton("📋 View Destinations", callback_data=f"view_destinations_{slot['id']}")],
        [InlineKeyboardButton("⚡ Toggle Active", callback_data=f"toggle_active_{slot['id']}")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu_slots")]
    ]
    
    status = "✅ Active" if slot['is_active'] else "❌ Inactive"
    destinations = len(slot.get('destinations', []))
    content_status = "Set" if slot.get('content') else "Not set"
    
    text = (
        f"🎯 **Managing Slot {slot_number}**\n\n"
        f"**Status:** {status}\n"
        f"**Destinations:** {destinations}/10\n"
        f"**Content:** {content_status}\n\n"
        "Choose an action:"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

@safe_error_handling
@safe_rate_limit("set_content_command")
async def set_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start setting content for a slot."""
    await update.message.reply_text(
        "📝 **Set Slot Content**\n\n"
        "Send the message you want to post to your destinations.\n\n"
        "You can send:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document with caption\n\n"
        "Or send /cancel to abort."
    )
    return ASK_SLOT_CONTENT

@safe_error_handling
async def set_content_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the content for a slot."""
    slot_id = context.user_data.get('managing_slot_id')
    if not slot_id:
        await update.message.reply_text("❌ No slot selected. Please try again.")
        return ConversationHandler.END
    
    db = context.bot_data['db']
    content = update.message.text or update.message.caption or ""
    file_id = None
    
    # Handle different message types
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    
    success = await db.update_slot_content(slot_id, content, file_id)
    
    if success:
        await update.message.reply_text("✅ Content saved successfully!")
    else:
        await update.message.reply_text("❌ Failed to save content. Please try again.")
    
    context.user_data.clear()
    return ConversationHandler.END

# Legacy methods for backward compatibility
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy settings menu - redirect to new UI."""
    await settings(update, context)

(ASK_ALIAS_ID, ASK_ALIAS_NAME) = range(20, 22)

async def set_alias_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start setting alias for a destination."""
    await update.message.reply_text(
        "Please send the ID of the destination you want to rename.\n"
        "(Find the ID with /list_destinations). Or /cancel."
    )
    return ASK_ALIAS_ID

async def ask_alias_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the new alias name."""
    try:
        dest_id = int(update.message.text)
        user_id = update.effective_user.id
        db = context.bot_data['db']
        destination = await db.get_destination_by_id(dest_id, user_id)
        
        if not destination:
            await update.message.reply_text("❌ Destination ID not found. Please try again or /cancel.")
            return ASK_ALIAS_ID
        
        context.user_data['alias_dest_id'] = dest_id
        await update.message.reply_text(f"OK. What new name would you like for '{destination.get('alias', destination['destination_name'])}'?")
        return ASK_ALIAS_NAME
        
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid ID. Please send a number, or /cancel.")
        return ASK_ALIAS_ID

async def save_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the new alias."""
    dest_id = context.user_data.get('alias_dest_id')
    if not dest_id:
        return await cancel(update, context)
    
    user_id = update.effective_user.id
    db = context.bot_data['db']
    success = await db.set_destination_alias(dest_id, user_id, update.message.text)
    
    if success:
        await update.message.reply_text(f"✅ Alias updated to '{update.message.text}'!")
    else:
        await update.message.reply_text("❌ Failed to update alias.")
    
    context.user_data.clear()
    return ConversationHandler.END
