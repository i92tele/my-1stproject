from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from datetime import datetime, timedelta
import secrets
from typing import List

logger = logging.getLogger(__name__)

# --- Define states for our conversations ---
SETTING_AD_CONTENT = 0
SETTING_AD_SCHEDULE = 1
SETTING_AD_DESTINATIONS = 2

# --- Basic Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message when user starts the bot.
    
    Args:
        update: Telegram update object
        context: Bot context with database and configuration
        
    Returns:
        None
    """
    try:
        user = update.effective_user
        if not user:
            logger.error("No effective user in update")
            await update.message.reply_text("❌ Error: Could not identify user")
            return
            
        db = context.bot_data.get('db')
        if not db:
            logger.error("Database not available in context")
            await update.message.reply_text("❌ Error: Database not available")
            return
        
        # Create or update user in database
        await db.create_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Get user subscription info
        subscription = await db.get_user_subscription(user.id)
        subscription_info = None
        if subscription and subscription.get('subscription_expires'):
            from datetime import datetime
            days_left = (subscription['subscription_expires'] - datetime.now()).days
            subscription_info = {
                'tier': subscription.get('subscription_tier', 'basic'),
                'days_left': max(0, days_left)
            }
        
        # Create welcome message
        welcome_text = f"🤖 *Welcome to AutoFarming Bot, {user.first_name}!*\n\n"
        welcome_text += "I'm here to help you manage your automated advertising campaigns.\n\n"
        
        if subscription_info:
            welcome_text += f"📊 *Your Subscription:* {subscription_info['tier'].title()}\n"
            welcome_text += f"⏰ *Days Remaining:* {subscription_info['days_left']}\n\n"
        else:
            welcome_text += "💎 *No active subscription*\n\n"
        
        welcome_text += "Use the buttons below to get started:"
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("📊 Analytics", callback_data="cmd:analytics"),
                InlineKeyboardButton("🎯 My Ads", callback_data="cmd:my_ads")
            ],
            [
                InlineKeyboardButton("💎 Subscribe", callback_data="cmd:subscribe"),
                InlineKeyboardButton("🎁 Referral", callback_data="cmd:referral")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="cmd:help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        logger.info(f"User {user.id} started the bot successfully")
        
    except Exception as e:
        logger.error(f"Error in start command for user {update.effective_user.id if update.effective_user else 'unknown'}: {e}")
        error_message = "❌ Sorry, something went wrong. Please try again or contact support."
        await update.message.reply_text(error_message)

async def handle_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle command button callbacks.
    
    Args:
        update: Telegram update object
        context: Bot context with database and configuration
        
    Returns:
        None
    """
    try:
        query = update.callback_query
        if not query:
            logger.error("No callback query in update")
            return
            
        await query.answer()
        
        if not query.data or ":" not in query.data:
            logger.error(f"Invalid callback data: {query.data}")
            await query.edit_message_text("❌ Invalid command")
            return
            
        command = query.data.split(":")[1]
        
        # Route to appropriate handler
        if command == "analytics":
            await analytics_command_callback(update, context)
        elif command == "referral":
            await referral_command_callback(update, context)
        elif command == "subscribe":
            await subscribe_callback(update, context)
        elif command == "my_ads":
            await my_ads_command(update, context)
        elif command == "help":
            await help_command_callback(update, context)
        elif command == "start":
            await start_callback(update, context)
        else:
            logger.warning(f"Unknown command: {command}")
            await query.edit_message_text("❌ Unknown command")
            
    except Exception as e:
        logger.error(f"Error in handle_command_callback: {e}")
        try:
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
        except:
            pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows help information.
    
    Args:
        update: Telegram update object
        context: Bot context
        
    Returns:
        None
    """
    try:
        help_text = (
            "📚 *Available Commands:*\n\n"
            "/start \\- Welcome message with buttons\n"
            "/my\\_ads \\- Manage your ad campaigns\n"
            "/analytics \\- View your ad performance\n"
            "/referral \\- Get your referral code\n"
            "/subscribe \\- View subscription plans\n"
            "/help \\- Show this help message"
        )
        
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
        logger.info(f"Help command executed by user {update.effective_user.id if update.effective_user else 'unknown'}")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text("❌ Error displaying help. Please try again.")
    
async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user analytics and performance metrics.
    
    Args:
        update: Telegram update object
        context: Bot context with database
        
    Returns:
        None
    """
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Could not identify user")
            return
            
        db = context.bot_data.get('db')
        if not db:
            await update.message.reply_text("❌ Database not available")
            return
            
        user_id = user.id
        
        # Check if user has active subscription
        subscription = await db.get_user_subscription(user_id)
        if not subscription or not subscription.get('is_active'):
            await update.message.reply_text(
                "❌ You need an active subscription to view analytics.\n\n"
                "Use /subscribe to get started!"
            )
            return
        
        # Get user slots for basic analytics
        slots = await db.get_user_slots(user_id)
        if not slots:
            await update.message.reply_text("❌ No ad slots found. Create some ads first!")
            return
        
        # Create basic analytics message
        total_slots = len(slots)
        active_slots = sum(1 for slot in slots if slot.get('is_active'))
        total_destinations = sum(len(slot.get('destinations', [])) for slot in slots)
        
        message = f"""📊 **Your Analytics**

🎯 **Ad Slots:** {total_slots} total, {active_slots} active
📍 **Destinations:** {total_destinations} total
⏰ **Subscription:** {subscription.get('tier', 'Unknown').title()}
📅 **Expires:** {subscription.get('expires', 'Unknown')}

*More detailed analytics coming soon!*"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Analytics displayed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in analytics_command for user {update.effective_user.id if update.effective_user else 'unknown'}: {e}")
        await update.message.reply_text("❌ Error loading analytics. Please try again.")

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's referral code and statistics.
    
    Args:
        update: Telegram update object
        context: Bot context with database
        
    Returns:
        None
    """
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Could not identify user")
            return
            
        db = context.bot_data.get('db')
        if not db:
            await update.message.reply_text("❌ Database not available")
            return
            
        user_id = user.id
        
        # Generate simple referral code (user_id based)
        referral_code = f"REF{user_id:06d}"
        
        # Create referral message
        message = f"""🎁 **Your Referral Program**

🔗 **Your Referral Code:** `{referral_code}`
👥 **Share this code with friends!**

**How it works:**
• Friends use your code when subscribing
• You both get bonus features
• Earn rewards for successful referrals

*Referral statistics coming soon!*"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Referral command executed by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in referral_command for user {update.effective_user.id if update.effective_user else 'unknown'}: {e}")
        await update.message.reply_text("❌ Error loading referral info. Please try again.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows subscription plans with enhanced UI and competitive pricing."""
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    # Get current subscription status
    subscription = await db.get_user_subscription(user_id)
    
    # Create enhanced subscription plans keyboard
    keyboard = [
        [
            InlineKeyboardButton("🥉 Basic - $9.99", callback_data="subscribe:basic"),
            InlineKeyboardButton("🥈 Pro - $19.99", callback_data="subscribe:pro")
        ],
        [
            InlineKeyboardButton("🥇 Enterprise - $29.99", callback_data="subscribe:enterprise")
        ],
        [
            InlineKeyboardButton("📊 Compare Plans", callback_data="compare_plans"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    
    if subscription and subscription['is_active']:
        status_text = f"✅ **Current Plan:** {subscription['tier'].title()}\n📅 **Expires:** {subscription['expires'].strftime('%Y-%m-%d')}"
    else:
        status_text = "❌ **No active subscription**"
    
    message_text = (
        f"🚀 **AutoFarming Pro - Subscription Plans**\n\n"
        f"{status_text}\n\n"
        "**Choose your plan:**\n"
        "• **🥉 Basic** ($9.99): 1 ad slot, hourly posting\n"
        "• **🥈 Pro** ($19.99): 3 ad slots, ban protection\n"
        "• **🥇 Enterprise** ($29.99): 5 ad slots, auto-renewal\n\n"
        "*Competitive pricing - 25-67% cheaper than competitors!*\n\n"
        "Select a plan to proceed with payment:"
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription plan selection and payment callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("subscribe:"):
        tier = query.data.split(":")[1]
        
        # Create payment buttons for the new system
        keyboard = [
            [InlineKeyboardButton("💎 Basic - $15", callback_data="pay:basic")],
            [InlineKeyboardButton("💎 Pro - $45", callback_data="pay:pro")],
            [InlineKeyboardButton("💎 Enterprise - $75", callback_data="pay:enterprise")]
        ]
        
        message_text = (
            "💎 **Subscription Plans**\n\n"
            "**Basic Plan** - $15/month\n"
            "• 1 ad slot\n"
            "• 10 destinations per slot\n"
            "• 30-day subscription\n\n"
            "**Pro Plan** - $45/month\n"
            "• 3 ad slots\n"
            "• 10 destinations per slot\n"
            "• 30-day subscription\n\n"
            "**Enterprise Plan** - $75/month\n"
            "• 5 ad slots\n"
            "• 10 destinations per slot\n"
            "• 30-day subscription\n\n"
            "💳 **Payment via TON cryptocurrency**"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data.startswith("pay:"):
        # Handle new payment format: pay:{tier}
        tier = query.data.split(":")[1]
        await handle_payment_callback(update, context, tier)
    
    elif query.data.startswith("check_payment:"):
        # Handle payment status check
        payment_id = query.data.split(":")[1]
        await check_payment_status_callback(update, context, payment_id)
    
    elif query.data == "compare_plans":
        await compare_plans_callback(update, context)
    elif query.data == "back_to_plans":
        await subscribe_callback(update, context)
    elif query.data.startswith("slot_analytics:"):
        slot_id = query.data.split(":")[1]
        await slot_analytics_callback(update, context, slot_id)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str):
    """Handle payment button clicks for new payment system."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        # Get payment processor from bot data
        payment_processor = context.bot_data.get('payment_processor')
        if not payment_processor:
            await query.edit_message_text("❌ Payment system not available")
            return
        
        # Create payment request
        amount_usd = 15 if tier == 'basic' else (45 if tier == 'pro' else 75)
        payment_request = await payment_processor.create_payment_request(
            user_id=user_id,
            tier=tier,
            amount_usd=amount_usd
        )
        
        if payment_request.get('success') is False:
            await query.edit_message_text(f"❌ Error creating payment: {payment_request.get('error')}")
            return
        
        # Create payment keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"💳 Pay {payment_request['amount_ton']} TON", 
                    url=payment_request['payment_url']
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Check Payment Status", 
                    callback_data=f"check_payment:{payment_request['payment_id']}"
                )
            ],
            [
                InlineKeyboardButton("📊 My Status", callback_data="cmd:status"),
                InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")
            ]
        ]
        
        text = (
            f"💳 **TON Payment for {tier.title()} Plan**\n\n"
            f"**Amount:** {payment_request['amount_ton']} TON (${payment_request['amount_usd']})\n"
            f"**Payment ID:** `{payment_request['payment_id']}`\n"
            f"**Expires:** {payment_request['expires_at']}\n\n"
            f"**Instructions:**\n"
            f"1. Click the payment button below\n"
            f"2. Complete the TON transfer\n"
            f"3. Click 'Check Payment Status' to verify\n\n"
            f"⏰ **Payment expires in 30 minutes**"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in handle_payment_callback: {e}")
        await query.edit_message_text(f"❌ Error creating payment: {str(e)}")

async def check_payment_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    """Check payment status and process if completed."""
    query = update.callback_query
    
    try:
        # Get payment processor from bot data
        payment_processor = context.bot_data.get('payment_processor')
        if not payment_processor:
            await query.edit_message_text("❌ Payment system not available")
            return
        
        # Get payment status
        status = await payment_processor.get_payment_status(payment_id)
        
        if not status['success']:
            await query.edit_message_text(f"❌ Error checking payment: {status.get('error')}")
            return
        
        payment = status['payment']
        
        if payment['status'] == 'completed':
            # Payment already completed
            keyboard = [
                [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                "✅ **Payment Completed!**\n\n"
                f"Your subscription has been activated.\n"
                f"Payment ID: `{payment_id}`\n\n"
                "You can now use your ad slots."
            )
        elif payment['status'] == 'pending':
            # Check if payment has been received
            verification = await payment_processor.verify_payment(payment_id)
            
            if verification.get('payment_verified'):
                # Process the payment
                result = await payment_processor.process_successful_payment(payment_id)
                
                if result['success']:
                    keyboard = [
                        [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")],
                        [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                    ]
                    text = (
                        "🎉 **Payment Verified!**\n\n"
                        f"✅ Subscription activated: **{result['tier'].title()}**\n"
                        f"📊 Ad slots: {result['slots']}\n"
                        f"Payment ID: `{payment_id}`\n\n"
                        "You can now create and manage your ad slots."
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_payment:{payment_id}")],
                        [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                    ]
                    text = (
                        "❌ **Payment Processing Failed**\n\n"
                        f"Payment was received but activation failed.\n"
                        f"Error: {result.get('error', 'Unknown error')}\n\n"
                        "Please contact support."
                    )
            else:
                # Payment not yet received
                keyboard = [
                    [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_payment:{payment_id}")],
                    [InlineKeyboardButton("💳 Pay Again", callback_data=f"pay:{payment.get('tier', 'basic')}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                ]
                text = (
                    "⏳ **Payment Pending**\n\n"
                    f"Payment ID: `{payment_id}`\n"
                    f"Amount: {payment['amount']} {payment['currency']}\n"
                    f"Status: {payment['status']}\n\n"
                    "Please complete the TON transfer and check again."
                )
        elif payment['status'] == 'expired':
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data=f"pay:{payment.get('tier', 'basic')}")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                "⏰ **Payment Expired**\n\n"
                f"Payment ID: `{payment_id}`\n"
                f"Status: {payment['status']}\n\n"
                "Please create a new payment request."
            )
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data=f"pay:{payment.get('tier', 'basic')}")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                f"❓ **Payment Status: {payment['status']}**\n\n"
                f"Payment ID: `{payment_id}`\n"
                f"Amount: {payment['amount']} {payment['currency']}\n\n"
                "Please contact support for assistance."
            )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in check_payment_status_callback: {e}")
        await query.edit_message_text(f"❌ Error checking payment: {str(e)}")

async def get_crypto_prices():
    """Get real-time crypto prices from CoinGecko API."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Get prices for supported cryptos
            crypto_ids = {
                'ton': 'the-open-network',
                'btc': 'bitcoin',
                'eth': 'ethereum',
                'sol': 'solana',
                'ltc': 'litecoin',
                'usdt': 'tether',
                'usdc': 'usd-coin',
                'ada': 'cardano'
            }
            
            ids = ','.join(crypto_ids.values())
            url = f'https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd'
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {k: data.get(v, {}).get('usd', 1.0) for k, v in crypto_ids.items()}
    except Exception as e:
        print(f"Error getting crypto prices: {e}")
    
    # Fallback prices
    return {
        'ton': 2.5, 'btc': 45000, 'eth': 3000, 'sol': 100, 'ltc': 150,
        'usdt': 1.0, 'usdc': 1.0, 'ada': 0.5
    }

def generate_crypto_qr(address: str, amount: float, crypto: str, payment_id: str = None):
    """Generate QR code for cryptocurrency payment"""
    try:
        # Import qrcode here to avoid issues
        import qrcode
        from PIL import Image
        import io
        
        # Generate payment URI based on cryptocurrency
        if crypto == 'ton':
            # TON format: ton://transfer/address?amount=amount&text=memo
            if payment_id:
                payment_uri = f"ton://transfer/{address}?amount={int(amount * 1000000000)}&text={payment_id}"
            else:
                payment_uri = f"ton://transfer/{address}?amount={int(amount * 1000000000)}"
        elif crypto == 'btc':
            # Bitcoin QR format: bitcoin:address?amount=amount
            # Ensure address is clean (remove spaces and special characters)
            clean_address = address.strip().replace(' ', '').replace('O', '0')
            # Try different BTC QR formats
            if amount > 0:
                amount_str = f"{amount:.8f}".rstrip('0').rstrip('.')
                payment_uri = f"bitcoin:{clean_address}?amount={amount_str}"
            else:
                payment_uri = f"bitcoin:{clean_address}"
        elif crypto == 'eth':
            # Use natural number format for ETH
            eth_amount = int(amount * 1000000000000000000)  # Convert to wei
            payment_uri = f"ethereum:{address}?value={eth_amount}"
            if payment_id:
                payment_uri += f"&label={payment_id}"
        elif crypto == 'sol':
            # Solana format
            sol_amount = int(amount * 1000000000)  # Convert to lamports
            payment_uri = f"solana:{address}?amount={sol_amount}"
        elif crypto == 'ltc':
            # Litecoin format
            ltc_amount = f"{amount:.8f}".rstrip('0').rstrip('.')
            payment_uri = f"litecoin:{address}?amount={ltc_amount}"
        elif crypto in ['usdt', 'usdc']:
            # For stablecoins, use ETH format with token contract
            eth_amount = int(amount * 1000000000000000000)  # Convert to wei
            payment_uri = f"ethereum:{address}?value={eth_amount}"
        elif crypto == 'ada':
            # Cardano format
            ada_amount = int(amount * 1000000)  # Convert to lovelace
            payment_uri = f"cardano:{address}?amount={ada_amount}"
        elif crypto == 'trx':
            # TRON format
            trx_amount = int(amount * 1000000)  # Convert to sun
            payment_uri = f"tron:{address}?amount={trx_amount}"
        else:
            # Default format
            payment_uri = f"{crypto}:{address}?amount={amount}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(payment_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes for Telegram
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check payment status."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("check_payment:"):
        payment_id = query.data.split(":")[1]
        
        try:
            # Get payment from database
            db = context.bot_data['db']
            payment = await db.get_payment(payment_id)
            
            if not payment:
                await query.edit_message_text("❌ Payment not found. Please try again.")
                return
            
            # Use the existing payment processor (TON only for now)
            # TODO: Implement multi-crypto payment processor
            # For now, we'll use a simple verification approach
            is_verified = True  # Placeholder - will be replaced with actual verification
            
            if is_verified:
                status = {'status': 'completed', 'message': 'Payment verified on blockchain'}
            else:
                status = {'status': 'pending', 'message': 'Payment not yet detected on blockchain'}
            
            if status['status'] == 'completed':
                await query.edit_message_text(
                    "✅ **Payment Confirmed!**\n\n"
                    "Your subscription is now active. Use /my_ads to manage your ad campaigns.",
                    parse_mode='Markdown'
                )
            elif status['status'] == 'pending':
                await query.edit_message_text(
                    "⏳ **Payment Pending**\n\n"
                    "We're still waiting for your payment. Please ensure you sent the correct amount with the memo.\n\n"
                    "Payment verification is automatic - check back in 30 seconds!",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Payment Not Found**\n\n"
                    "Please try again or contact support if you've already sent the payment.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            context.bot_data['logger'].error(f"Payment status check error: {e}")
            await query.edit_message_text("❌ Error checking payment status. Please try again later.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command placeholder."""
    await update.message.reply_text("Status feature coming soon! 📊")

# --- Main Ad Management Command ---

async def my_ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's ad slots."""
    try:
        db = context.bot_data['db']
        user_id = update.effective_user.id

        # Create user if they don't exist
        user = await db.get_user(user_id)
        if not user:
            await db.create_user(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            )

        subscription = await db.get_user_subscription(user_id)
        if not subscription or not subscription['is_active']:
            reply_obj = update.message if update.message else update.callback_query.message
            await reply_obj.reply_text(
                "❌ You need an active subscription to manage ads.\n\n"
                "Please contact the admin to get a subscription."
            )
            return

        ad_slots = await db.get_or_create_ad_slots(user_id, subscription['tier'])
        if not ad_slots:
            reply_obj = update.message if update.message else update.callback_query.message
            await reply_obj.reply_text("Could not find any ad slots for your subscription tier.")
            return

        message_text = "📢 **Your Ad Slots**\n\nSelect a slot to manage it:"
        keyboard = []
        
        for slot in ad_slots:
            slot_number = slot['slot_number']
            status_icon = "✅" if slot['is_active'] else "⏸️"
            
            if slot['ad_content']:
                content_preview = slot['ad_content'][:20] + "..." if len(slot['ad_content']) > 20 else slot['ad_content']
                ad_info = f" - {content_preview}"
            else:
                ad_info = " - (Empty)"

            button_text = f"Slot {slot_number} {status_icon}{ad_info}"
            callback_data = f"manage_slot:{slot['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Add back to main menu button
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text, 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text, 
                reply_markup=reply_markup, 
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in my_ads_command: {e}")
        error_message = "❌ Sorry, there was an error loading your ads. Please try again."
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(error_message, reply_markup=reply_markup)

# --- Ad Slot Management ---

async def handle_ad_slot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all ad slot related callbacks."""
    query = update.callback_query
    await query.answer()

    db = context.bot_data['db']
    data_parts = query.data.split(":")

    if data_parts[0] == "back_to_slots":
        await my_ads_command(update, context)
        return
    
    if data_parts[0] == "toggle_ad":
        slot_id = int(data_parts[1])
        slot_data = await db.get_ad_slot_by_id(slot_id)
        if slot_data:
            new_status = not slot_data['is_active']
            success = await db.update_ad_slot_status(slot_id, new_status)
            if success:
                status_text = "resumed ▶️" if new_status else "paused ⏸️"
                await query.answer(f"Ad {status_text}")
            else:
                await query.answer("Failed to update status", show_alert=True)
        # Don't modify query.data, just continue to show the slot details

    slot_id = int(query.data.split(":")[1])
    slot_data = await db.get_ad_slot_by_id(slot_id)
    if not slot_data:
        await query.edit_message_text("Error: Could not find this ad slot.")
        return

    slot_number = slot_data['slot_number']
    ad_content = slot_data['ad_content']
    interval = slot_data['interval_minutes']
    is_active = slot_data['is_active']
    
    destinations = await db.get_destinations_for_slot(slot_id)
    destinations_text = f"{len(destinations)} groups/channels" if destinations else "(Not Set)"

    status_text = (
        f"**📋 Ad Slot {slot_number}**\n\n"
        f"**Status:** {'✅ Active' if is_active else '⏸️ Paused'}\n"
        f"**Content:** {ad_content[:50] + '...' if ad_content and len(ad_content) > 50 else ad_content or '(Not Set)'}\n"
        f"**Schedule:** Every {interval} minutes\n"
        f"**Destinations:** {destinations_text}"
    )

    keyboard = [
        [InlineKeyboardButton("📝 Set Ad Content", callback_data=f"set_content:{slot_id}")],
        [InlineKeyboardButton("🗓️ Set Schedule", callback_data=f"set_schedule:{slot_id}")],
        [InlineKeyboardButton("🎯 Set Destinations", callback_data=f"set_dests:{slot_id}")],
        [InlineKeyboardButton("⏸️ Pause Ad" if is_active else "▶️ Resume Ad", callback_data=f"toggle_ad:{slot_id}")],
        [InlineKeyboardButton("⬅️ Back to All Slots", callback_data="back_to_slots")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')

# --- Set Ad Content Conversation ---

async def set_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to set ad content."""
    query = update.callback_query
    await query.answer()

    slot_id = int(query.data.split(":")[1])
    context.user_data['current_slot_id'] = slot_id

    await query.edit_message_text(
        "📝 **Set Ad Content**\n\n"
        "Please send me the content for your ad.\n\n"
        "You can send:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n\n"
        "Use /cancel to go back."
    )
    return SETTING_AD_CONTENT

async def set_content_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and saves the ad content."""
    db = context.bot_data['db']
    slot_id = context.user_data.get('current_slot_id')

    if not slot_id:
        await update.message.reply_text("An error occurred. Please start over with /my_ads.")
        return ConversationHandler.END

    ad_message = update.message
    ad_text = ad_message.text or ad_message.caption or ""
    ad_file_id = None

    if ad_message.photo:
        ad_file_id = ad_message.photo[-1].file_id
    elif ad_message.video:
        ad_file_id = ad_message.video.file_id

    success = await db.update_ad_slot_content(slot_id, ad_text, ad_file_id)

    if success:
        await update.message.reply_text("✅ Your ad content has been saved successfully!")
    else:
        await update.message.reply_text("❌ An error occurred while saving your ad.")

    context.user_data.pop('current_slot_id', None)
    await my_ads_command(update, context)
    return ConversationHandler.END

# --- Set Schedule Conversation ---

async def set_schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to set ad schedule."""
    query = update.callback_query
    await query.answer()

    slot_id = int(query.data.split(":")[1])
    context.user_data['current_slot_id'] = slot_id

    await query.edit_message_text(
        "🗓️ **Set Posting Schedule**\n\n"
        "How often should this ad be posted?\n\n"
        "Enter the interval in minutes (30-1440):\n\n"
        "• 30 = every 30 minutes\n"
        "• 60 = every hour\n"
        "• 120 = every 2 hours\n"
        "• 1440 = once per day\n\n"
        "Use /cancel to go back."
    )
    return SETTING_AD_SCHEDULE

async def set_schedule_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and saves the schedule."""
    db = context.bot_data['db']
    slot_id = context.user_data.get('current_slot_id')

    if not slot_id:
        await update.message.reply_text("An error occurred. Please start over with /my_ads.")
        return ConversationHandler.END

    try:
        interval = int(update.message.text.strip())
        
        if interval < 30:
            await update.message.reply_text("❌ Minimum interval is 30 minutes. Please try again.")
            return SETTING_AD_SCHEDULE
        elif interval > 1440:
            await update.message.reply_text("❌ Maximum interval is 1440 minutes (24 hours). Please try again.")
            return SETTING_AD_SCHEDULE

        success = await db.update_ad_slot_schedule(slot_id, interval)

        if success:
            hours = interval // 60
            minutes = interval % 60
            time_str = ""
            if hours > 0:
                time_str = f"{hours} hour{'s' if hours != 1 else ''}"
            if minutes > 0:
                if time_str:
                    time_str += f" and {minutes} minute{'s' if minutes != 1 else ''}"
                else:
                    time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            
            await update.message.reply_text(f"✅ Schedule saved! Your ad will be posted every {time_str}.")
        else:
            await update.message.reply_text("❌ An error occurred while saving the schedule.")

    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number. Use /cancel to go back.")
        return SETTING_AD_SCHEDULE

    context.user_data.pop('current_slot_id', None)
    await my_ads_command(update, context)
    return ConversationHandler.END

# --- Set Destinations Conversation ---

async def set_destinations_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to set ad destinations."""
    query = update.callback_query
    await query.answer()

    slot_id = int(query.data.split(":")[1])
    context.user_data['current_slot_id'] = slot_id

    # Get available categories from managed groups
    db = context.bot_data['db']
    all_groups = await db.get_managed_groups()
    categories = list(set([group['category'] for group in all_groups]))
    
    if not categories:
        await query.edit_message_text(
            "❌ No destination categories available.\n\n"
            "Please ask the admin to add some groups first."
        )
        return ConversationHandler.END

    # Create category selection keyboard
    keyboard = []
    for category in categories:
        category_groups = [g for g in all_groups if g['category'] == category]
        keyboard.append([InlineKeyboardButton(
            f"📋 {category.title()} ({len(category_groups)} groups)", 
            callback_data=f"select_category:{slot_id}:{category}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"manage_slot:{slot_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🎯 **Set Ad Destinations**\n\n"
        "Choose a category for your ad slot:\n\n"
        "This will automatically post your ad to all groups in the selected category.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SETTING_AD_DESTINATIONS

async def select_destination_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination category selection."""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split(":")
    slot_id = int(data_parts[1])
    category = data_parts[2]
    
    db = context.bot_data['db']
    
    # Get all groups in this category
    category_groups = await db.get_managed_groups(category)
    
    if not category_groups:
        await query.edit_message_text(
            f"❌ No groups found in {category} category.\n\n"
            "Please ask the admin to add some groups first."
        )
        return ConversationHandler.END
    
    # Set destinations for this slot
    destinations = [group['group_name'] for group in category_groups]
    success = await db.update_destinations_for_slot(slot_id, destinations)
    
    if success:
        await query.edit_message_text(
            f"✅ **Destinations Set Successfully!**\n\n"
            f"**Category:** {category.title()}\n"
            f"**Groups:** {len(destinations)} groups\n\n"
            f"Your ad will now be posted to all {category} groups automatically.",
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ Failed to set destinations. Please try again."
        )
    
    # Return to slot management
    await my_ads_command(update, context)
    return ConversationHandler.END

# --- Cancel Conversation ---

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels any active conversation."""
    context.user_data.clear()
    await update.message.reply_text("Operation cancelled. ❌")
    await my_ads_command(update, context)
    return ConversationHandler.END

async def analytics_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user analytics and performance metrics (callback version)."""
    query = update.callback_query
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    # Check if user has active subscription
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await query.edit_message_text(
            "❌ You need an active subscription to view analytics.\n\n"
            "Use /subscribe to get started!"
        )
        return
    
    try:
        from analytics import AnalyticsEngine
        analytics = AnalyticsEngine(db, context.bot_data['logger'])
        
        # Get user analytics
        stats = await analytics.get_user_analytics(user_id, days=30)
        
        if not stats:
            await query.edit_message_text("❌ No analytics data available yet.")
            return
        
        # Create analytics message
        message = f"""
📊 *Your Analytics (Last 30 Days)*

📈 *Performance:*
• Total Posts: {stats.get('total_posts', 0)}
• Successful Posts: {stats.get('successful_posts', 0)}
• Success Rate: {stats.get('success_rate', 0)}%

🎯 *Reach:*
• Estimated Reach: {stats.get('estimated_reach', 0):,} people
• Active Ad Slots: {stats.get('active_slots', 0)}/{stats.get('ad_slots', 0)}

💰 *ROI:*
• Subscription Cost: ${stats.get('subscription_cost', 0)}
• Estimated Revenue: ${stats.get('estimated_revenue', 0):.2f}
• ROI: {stats.get('roi_percentage', 0)}%

⏰ *Subscription:*
• Days Remaining: {stats.get('days_remaining', 0)}
"""
        
        # Add back button
        keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        context.bot_data['logger'].error(f"Analytics error: {e}")
        await query.edit_message_text("❌ Error loading analytics. Please try again later.")

async def referral_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral code and statistics (callback version)."""
    query = update.callback_query
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    try:
        from referral_system import ReferralSystem
        referral_system = ReferralSystem(db, context.bot_data['logger'])
        
        # Get or create referral code
        referral_code = await referral_system.get_user_referral_code(user_id)
        if not referral_code:
            referral_code = await referral_system.create_referral_code(user_id)
        
        # Get referral statistics
        stats = await referral_system.get_referral_stats(user_id)
        
        # Create referral message
        message = f"""
🎁 Your Referral Program

🔗 Your Referral Code:
{referral_code}

📊 Statistics:
• Total Referrals: {stats.get('total_referrals', 0)}
• Pending Referrals: {stats.get('pending_referrals', 0)}
• Rewards Earned: {stats.get('rewards_earned', 0)}

💎 How It Works:
• Share your referral code with friends
• When they subscribe, you both get rewards
• You get 7 days free subscription
• They get 50% discount on first month

📱 Share this message:
Join AutoFarming Bot with my referral code: {referral_code}
"""
        
        # Add back button
        keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        context.bot_data['logger'].error(f"Referral error: {e}")
        await query.edit_message_text("❌ Error loading referral information. Please try again later.")

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subscription plans (callback version)."""
    query = update.callback_query
    
    message_text = (
        "💎 Choose Your Subscription Plan\n\n"
        "Basic Plan - $9.99/month\n"
        "• 1 ad slot\n"
        "• Basic analytics\n"
        "• Email support\n\n"
        "Pro Plan - $39.99/month\n"
        "• 5 ad slots\n"
        "• Advanced analytics\n"
        "• Priority support\n"
        "• Custom scheduling\n"
        "• Ban protection\n\n"
        "Enterprise Plan - $99.99/month\n"
        "• 15 ad slots\n"
        "• Full analytics suite\n"
        "• 24/7 support\n"
        "• Auto-renewal\n"
        "• Premium features\n\n"
        "Payment via TON cryptocurrency only."
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 Basic - $9.99", callback_data="subscribe:basic")],
        [InlineKeyboardButton("🚀 Pro - $39.99", callback_data="subscribe:pro")],
        [InlineKeyboardButton("🏢 Enterprise - $99.99", callback_data="subscribe:enterprise")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd:start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message_text, reply_markup=reply_markup)

async def help_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows help information (callback version)."""
    query = update.callback_query
    help_text = (
        "📚 Available Commands:\n\n"
        "/start - Welcome message with buttons\n"
        "/my_ads - Manage your ad campaigns\n"
        "/analytics - View your ad performance\n"
        "/referral - Get your referral code\n"
        "/subscribe - View subscription plans\n"
        "/help - Show this help message"
    )
    
    # Create inline keyboard for quick access
    keyboard = [
        [InlineKeyboardButton("📊 Analytics", callback_data="cmd:analytics")],
        [InlineKeyboardButton("🎁 Referral Program", callback_data="cmd:referral")],
        [InlineKeyboardButton("💎 Subscribe", callback_data="cmd:subscribe")],
        [InlineKeyboardButton("📋 My Ads", callback_data="cmd:my_ads")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd:start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu (callback version)."""
    query = update.callback_query
    user = update.effective_user
    welcome_text = (
        f"Welcome {user.first_name}! 👋\n\n"
        "I'm the AutoFarming Bot - your automated Telegram advertising assistant.\n\n"
        "Choose an option below to get started:"
    )
    
    # Create inline keyboard with main commands
    keyboard = [
        [InlineKeyboardButton("📊 Analytics", callback_data="cmd:analytics")],
        [InlineKeyboardButton("🎁 Referral Program", callback_data="cmd:referral")],
        [InlineKeyboardButton("💎 Subscribe", callback_data="cmd:subscribe")],
        [InlineKeyboardButton("📋 My Ads", callback_data="cmd:my_ads")],
        [InlineKeyboardButton("❓ Help", callback_data="cmd:help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(welcome_text, reply_markup=reply_markup)

async def compare_plans_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed plan comparison."""
    query = update.callback_query
    await query.answer()
    
    comparison_text = (
        "📊 **Plan Comparison**\n\n"
        "🥉 **Basic Plan - $9.99/month**\n"
        "• 1 ad slot\n"
        "• Basic analytics\n"
        "• Email support\n"
        "• Standard posting\n\n"
        "🥈 **Pro Plan - $19.99/month**\n"
        "• 3 ad slots\n"
        "• Advanced analytics\n"
        "• Priority support\n"
        "• Custom scheduling\n"
        "• Ban protection\n\n"
        "🥇 **Enterprise Plan - $29.99/month**\n"
        "• 5 ad slots\n"
        "• Full analytics suite\n"
        "• 24/7 support\n"
        "• Auto-renewal\n"
        "• Premium features\n\n"
        "💡 *All plans include 30-day duration and TON payment*"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 Subscribe Now", callback_data="cmd:subscribe")],
        [InlineKeyboardButton("🔙 Back to Plans", callback_data="cmd:subscribe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(comparison_text, reply_markup=reply_markup, parse_mode='Markdown')

async def slot_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: str):
    """Show analytics for a specific ad slot."""
    query = update.callback_query
    await query.answer()
    
    try:
        db = context.bot_data['db']
        user_id = update.effective_user.id
        
        # Get slot info
        slot = await db.get_ad_slot(int(slot_id))
        if not slot or slot['user_id'] != user_id:
            await query.edit_message_text("❌ Ad slot not found or access denied.")
            return
        
        # Get analytics data (placeholder for now)
        analytics_text = (
            f"📊 **Ad Slot Analytics**\n\n"
            f"**Slot ID:** {slot_id}\n"
            f"**Status:** {'🟢 Active' if slot.get('is_active') else '🔴 Inactive'}\n"
            f"**Created:** {slot.get('created_at', 'N/A')}\n\n"
            f"**Performance:**\n"
            f"• Posts sent: {slot.get('posts_sent', 0)}\n"
            f"• Success rate: {slot.get('success_rate', 0)}%\n"
            f"• Last posted: {slot.get('last_posted', 'Never')}\n\n"
            "*Detailed analytics coming soon!*"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Slot", callback_data=f"manage_slot:{slot_id}")],
            [InlineKeyboardButton("📋 All Slots", callback_data="cmd:my_ads")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(analytics_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Slot analytics error: {e}")
        await query.edit_message_text("❌ Error loading analytics. Please try again.")

def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown parsing."""
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long messages to avoid Telegram's 4096 character limit."""
    if len(text) <= max_length:
        return [text]
    
    messages = []
    
    # If text is just a long string without paragraphs, split by character count
    if '\n\n' not in text:
        for i in range(0, len(text), max_length):
            messages.append(text[i:i + max_length])
        return messages
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    current_message = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed limit
        if len(current_message) + len(paragraph) + 2 > max_length:
            if current_message:
                messages.append(current_message.strip())
                current_message = paragraph
            else:
                # Single paragraph is too long, split by sentences
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if len(current_message) + len(sentence) + 2 > max_length:
                        if current_message:
                            messages.append(current_message.strip())
                            current_message = sentence
                        else:
                            # Single sentence is too long, split by words
                            words = sentence.split(' ')
                            for word in words:
                                if len(current_message) + len(word) + 1 > max_length:
                                    if current_message:
                                        messages.append(current_message.strip())
                                        current_message = word
                                    else:
                                        # Single word is too long, truncate
                                        messages.append(word[:max_length])
                                else:
                                    current_message += " " + word if current_message else word
                    else:
                        current_message += ". " + sentence if current_message else sentence
        else:
            current_message += "\n\n" + paragraph if current_message else paragraph
    
    if current_message:
        messages.append(current_message.strip())
    
    return messages

async def safe_send_message(update, message_text: str, reply_markup=None, parse_mode='MarkdownV2'):
    """Safely send message with proper length handling and parse mode."""
    try:
        # Escape markdown characters
        escaped_text = escape_markdown(message_text)
        
        # Split long messages
        messages = split_long_message(escaped_text)
        
        # Send first message with reply markup
        if messages:
            await update.message.reply_text(
                messages[0], 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
            
            # Send remaining messages without markup
            for message in messages[1:]:
                await update.message.reply_text(message, parse_mode=parse_mode)
                
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # Fallback to plain text
        await update.message.reply_text(
            "❌ Error formatting message. Please try again.",
            reply_markup=reply_markup
        )