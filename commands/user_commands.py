from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    db = context.bot_data['db']
    ui = context.bot_data['ui']

    await db.create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    subscription = await db.get_user_subscription(user.id)
    context_data = {'has_subscription': subscription and subscription['is_active']}
    
    welcome_text = ui.format_welcome_message(user.first_name).replace('*', '') # Remove markdown characters
    keyboard = ui.get_main_menu_keyboard(context_data)

    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "Available Commands:\n\n"
        "Basic Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status - Check your subscription status\n\n"
        "Subscription:\n"
        "/subscribe - View subscription plans\n\n"
        "Forwarding:\n"
        "/add_destination - Add a new forwarding destination\n"
        "/list_destinations - See your current destinations\n"
        "/remove_destination - Remove a destination\n\n"
        "Other:\n"
        "/cancel - Cancel the current operation"
    )
    await update.message.reply_text(help_text)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command."""
    ui = context.bot_data['ui']
    db = context.bot_data['db']
    user_id = update.effective_user.id
    subscription = await db.get_user_subscription(user_id)
    current_tier = subscription['tier'] if subscription and subscription['is_active'] else None
    keyboard = ui.get_subscription_keyboard(current_tier)
    text = "Subscription Plans\n\nChoose a plan to see more details."
    await update.message.reply_text(
        text,
        reply_markup=keyboard
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        status_text = "Your Status:\n\nNo active subscription.\n\nUse /subscribe to get started!"
    else:
        expires = subscription['expires']
        days_left = (expires - datetime.now()).days
        destinations = await db.get_destinations(user_id)
        config = context.bot_data['config']
        tier_info = config.get_tier_info(subscription['tier'])
        max_dest = tier_info['max_destinations'] if tier_info['max_destinations'] > 0 else 'Unlimited'
        status_text = (
            f"Your Status:\n\n"
            f"Active Subscription\n"
            f"Plan: {subscription['tier'].title()}\n"
            f"Expires: {expires.strftime('%Y-%m-%d')} ({days_left} days left)\n"
            f"Active Destinations: {len(destinations)}/{max_dest}"
        )
    await update.message.reply_text(status_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled.")

# Callback handlers
async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ui = context.bot_data['ui']
    if data.startswith("view_tier:"):
        tier = data.split(":")[1]
        text = ui.format_tier_details(tier).replace('*', '') # Remove markdown characters
        keyboard = ui.get_payment_method_keyboard(tier)
        await query.edit_message_text(text, reply_markup=keyboard)
    elif data == "main_menu":
        await subscribe(update.callback_query, context)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    payments = context.bot_data['payments']
    ui = context.bot_data['ui']
    parts = data.split(":")
    if len(parts) != 3:
        return
    tier, crypto = parts[1], parts[2]
    try:
        payment_data = await payments.create_payment(user_id=update.effective_user.id, tier=tier, crypto=crypto)
        qr_code = await payments.generate_payment_qr(payment_data)
        instructions = ui.format_payment_instructions(payment_data).replace('*', '').replace('`', '') # Remove markdown
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Verify", callback_data=f"v:{payment_data['payment_id']}")]])
        await query.edit_message_text("Generating payment details...")
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=qr_code, caption=instructions, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await query.answer("Error creating payment.")
async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for How It Works."""
    await update.message.reply_text("This feature is coming soon!")

async def pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for Pricing."""
    # This can be the same as /subscribe for now
    await subscribe(update, context)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for Support."""
    await update.message.reply_text("For support, please contact the admin.")
