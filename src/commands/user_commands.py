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
    
    # Create or update user record
    await db.create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Get user data for menu
    user_data = await db.get_user(user.id)
    subscription = await db.get_user_subscription(user.id)
    
    context_data = {
        'has_subscription': subscription and subscription['is_active']
    }
    
    # Send welcome message with main menu
    welcome_text = ui.format_welcome_message(user.first_name)
    keyboard = ui.get_main_menu_keyboard(context_data)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
?? **Available Commands:**

**Basic Commands:**
/start - Start the bot
/help - Show this help message
/status - Check your subscription status

**Subscription:**
/subscribe - View subscription plans

**Forwarding:**
/add_destination - Add a forwarding destination
/list_destinations - List your destinations
/remove_destination - Remove a destination

**Other:**
/cancel - Cancel current operation

For support, contact the admin.
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command."""
    ui = context.bot_data['ui']
    db = context.bot_data['db']
    
    user_id = update.effective_user.id
    subscription = await db.get_user_subscription(user_id)
    
    current_tier = subscription['tier'] if subscription and subscription['is_active'] else None
    
    keyboard = ui.get_subscription_keyboard(current_tier)
    
    text = """
?? **Subscription Plans**

Choose the plan that best fits your needs:

?? **Basic** - $5/month
• Forward to 3 destinations
• 1,000 messages/day
• Basic filters

?? **Premium** - $15/month
• Forward to 10 destinations
• 10,000 messages/day
• Advanced filters
• Priority support

?? **Professional** - $30/month
• Unlimited destinations
• Unlimited messages
• All features included
• VIP support

Select a plan below to see more details:
"""
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    # Get user subscription info
    subscription = await db.get_user_subscription(user_id)
    
    if not subscription or not subscription['is_active']:
        status_text = """
?? **Your Status:**

? No active subscription

Use /subscribe to get started!
        """
    else:
        expires = subscription['expires']
        days_left = (expires - datetime.now()).days
        
        # Get user's destinations
        destinations = await db.get_destinations(user_id)
        
        # Get tier info
        config = context.bot_data['config']
        tier_info = config.get_tier_info(subscription['tier'])
        
        status_text = f"""
?? **Your Status:**

? Active Subscription
?? Plan: {subscription['tier'].title()}
?? Expires: {expires.strftime('%Y-%m-%d')} ({days_left} days left)
?? Active Destinations: {len(destinations)}/{tier_info['max_destinations'] if tier_info['max_destinations'] > 0 else '8'}

Use /list_destinations to see your forwarding destinations.
        """
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command."""
    # Clear any ongoing conversation states
    context.user_data.clear()
    
    await update.message.reply_text(
        "? Operation cancelled. How can I help you?",
        reply_markup=None
    )

# Callback handlers

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription selection callbacks."""
    query = update.callback_query
    data = query.data
    ui = context.bot_data['ui']
    
    if data.startswith("view_tier:"):
        tier = data.split(":")[1]
        
        # Show tier details
        text = ui.format_tier_details(tier)
        keyboard = ui.get_payment_method_keyboard(tier)
        
        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif data == "compare_plans":
        # Show plan comparison
        comparison_text = """
?? **Plan Comparison**

**Features** | **Basic** | **Premium** | **Pro**
:--|:--:|:--:|:--:
Price | $5/mo | $15/mo | $30/mo
Destinations | 3 | 10 | Unlimited
Messages/day | 1,000 | 10,000 | Unlimited
Keyword filters | ? | ? | ?
Advanced filters | ? | ? | ?
Schedule filters | ? | ? | ?
Priority support | ? | ? | ?
API access | ? | ? | ?
Custom features | ? | ? | ?

Choose the plan that fits your needs!
"""
        
        keyboard = ui.get_subscription_keyboard()
        
        await query.edit_message_text(
            comparison_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif data == "main_menu":
        await subscribe(update, context)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection callbacks."""
    query = update.callback_query
    data = query.data
    
    payments = context.bot_data['payments']
    ui = context.bot_data['ui']
    
    # Parse callback data: pay:tier:crypto
    parts = data.split(":")
    if len(parts) != 3:
        await query.answer("Invalid payment data")
        return
    
    tier = parts[1]
    crypto = parts[2]
    
    try:
        # Create payment
        payment_data = await payments.create_payment(
            user_id=update.effective_user.id,
            tier=tier,
            crypto=crypto
        )
        
        # Generate QR code
        qr_code = await payments.generate_payment_qr(payment_data)
        
        # Format payment instructions
        instructions = ui.format_payment_instructions(payment_data)
        
        # Create payment verification keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("? Verify Payment", callback_data=f"verify:{payment_data['payment_id']}")],
            [InlineKeyboardButton("? Cancel", callback_data="cancel_payment")]
        ])
        
        # Send payment instructions with QR code
        await query.message.reply_photo(
            photo=qr_code,
            caption=instructions,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        await query.edit_message_text("Payment details sent! Check the message below.")
        
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await query.answer("Error creating payment. Please try again.")
        await query.edit_message_text(
            "? Error creating payment. Please try again or contact support."
        )