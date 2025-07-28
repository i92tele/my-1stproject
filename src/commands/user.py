from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from ..decorators import rate_limit

@rate_limit()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = context.bot_data['db']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    await db.create_or_update_user(user_id=user.id, username=user.username, first_name=user.first_name, last_name=user.last_name)
    welcome_text = (f"👋 Welcome {user.first_name}!\n\nI'm a message forwarding bot. Use the buttons below or /help to see what I can do.")
    keyboard = [[InlineKeyboardButton("💎 View Subscription Plans", callback_data="start_subscribe")], [InlineKeyboardButton("❓ How It Works", callback_data="start_help")]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

@rate_limit()
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = ("📚 **Available Commands:**\n\n/start - Main menu\n/help - This message\n/settings - Open settings\n"
                 "/subscribe - View plans\n/status - Check subscription\n/list_destinations - View your destinations\n"
                 "/add_destination - Add a destination\n/set_alias - Rename a destination\n/cancel - Cancel an operation")
    message = update.callback_query.message if update.callback_query else update.message
    if update.callback_query: await update.callback_query.answer()
    await message.reply_text(help_text, parse_mode='Markdown')

@rate_limit()
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = context.bot_data['config']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    keyboard = [[InlineKeyboardButton(f"{name.title()} - ${info['price']:.2f}/mo", callback_data=f"subscribe_{name}")] for name, info in config.subscription_tiers.items()]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")])
    text = "💎 **Subscription Plans**\n\nChoose a plan:"
    for name, info in config.subscription_tiers.items(): text += f"\n\n**{name.title()}**: {info['description']}"
    message = update.callback_query.message if update.callback_query else update.message
    if update.callback_query:
        await update.callback_query.answer()
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

@rate_limit()
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = context.bot_data['db']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    subscription = await db.get_user_subscription(user_id)
    keyboard = None
    if not subscription or not subscription['is_active']:
        status_text = "📊 **Your Status:**\n\n❌ No active subscription"
        keyboard = [[InlineKeyboardButton("💎 View Plans", callback_data="start_subscribe")]]
    else:
        expires = datetime.fromisoformat(subscription['expires'])
        days_left = (expires - datetime.now()).days
        destinations = await db.get_destinations(user_id)
        status_text = (f"📊 **Your Status:**\n\n✅ Plan: **{subscription['tier'].title()}**\n"
                       f"📅 Expires: {expires.strftime('%Y-%m-%d')} ({days_left} days left)\n🎯 Destinations: {len(destinations)}")
        keyboard = [[InlineKeyboardButton("Renew / Upgrade", callback_data="start_subscribe")]]
    message = update.callback_query.message if update.callback_query else update.message
    if update.callback_query:
        await update.callback_query.answer()
        await message.edit_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode='Markdown')
    else:
        await message.reply_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message_text = "Operation cancelled."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message_text)
    else:
        await update.message.reply_text(message_text)
    return ConversationHandler.END

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("💳 Subscription Status", callback_data="settings_status")],
                [InlineKeyboardButton("🎯 Manage Destinations", callback_data="settings_destinations")],
                [InlineKeyboardButton("❌ Close", callback_data="cancel_action")]]
    await update.message.reply_text("⚙️ **Settings Menu**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

(ASK_ALIAS_ID, ASK_ALIAS_NAME) = range(10, 12)
async def set_alias_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send the ID of the destination you want to rename.\n(Find the ID with /list_destinations). Or /cancel.")
    return ASK_ALIAS_ID

async def ask_alias_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        dest_id = int(update.message.text)
        destination = await context.bot_data['db'].get_destination_by_id(dest_id, update.effective_user.id)
        if not destination:
            await update.message.reply_text("❌ Destination ID not found. Please try again or /cancel.")
            return ASK_ALIAS_ID
        context.user_data['alias_dest_id'] = dest_id
        await update.message.reply_text(f"OK. What new name would you like for '{destination['alias']}'?")
        return ASK_ALIAS_NAME
    except (ValueError, TypeError):
        await update.message.reply_text("Invalid ID. Please send a number, or /cancel.")
        return ASK_ALIAS_ID

async def save_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dest_id = context.user_data.get('alias_dest_id')
    if not dest_id:
        return await cancel(update, context)
    success = await context.bot_data['db'].set_destination_alias(dest_id, update.effective_user.id, update.message.text)
    await update.message.reply_text(f"✅ Alias updated to '{update.message.text}'!" if success else "❌ Failed to update alias.")
    context.user_data.clear()
    return ConversationHandler.END
