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
        
        # Create or update user in database (preserves subscription via UPSERT)
        await db.create_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Get user subscription info
        subscription = await db.get_user_subscription(user.id)
        subscription_info = None
        if subscription and subscription.get('expires'):
            from datetime import datetime
            # subscription['expires'] may be a string or datetime depending on sqlite adapter
            expires_value = subscription['expires']
            if isinstance(expires_value, str):
                try:
                    # Try ISO format first
                    expires_dt = datetime.fromisoformat(expires_value)
                except Exception:
                    # Fallback: try parsing common sqlite timestamp format
                    try:
                        from datetime import datetime as _dt
                        expires_dt = _dt.strptime(expires_value, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        expires_dt = datetime.now()
            else:
                expires_dt = expires_value
            days_left = max(0, (expires_dt - datetime.now()).days)
            subscription_info = {
                'tier': subscription.get('tier', 'basic'),
                'days_left': max(0, days_left)
            }
        
        # Create welcome message
        welcome_text = f"🤖 *Welcome to AutoFarming Bot, {user.first_name}!*\n\n"
        welcome_text += "I'm here to help you manage your automated advertising campaigns.\n\n"
        
        if subscription and subscription.get('is_active'):
            tier = (subscription.get('tier') or 'basic').title()
            if subscription_info:
                welcome_text += f"📊 *Your Subscription:* {tier}\n"
                welcome_text += f"⏰ *Days Remaining:* {subscription_info['days_left']}\n\n"
            else:
                welcome_text += f"📊 *Your Subscription:* {tier}\n\n"
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
        elif command == "admin_menu":
            # Import admin commands to handle admin menu
            try:
                from commands import admin_commands
                await admin_commands.admin_menu(update, context)
            except ImportError:
                logger.warning("Admin commands not available")
                await query.edit_message_text("❌ Admin features not available")
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
        try:
            slots = await db.get_or_create_ad_slots(user_id, subscription.get('tier', 'basic'))
            if not slots:
                await update.message.reply_text("❌ No ad slots found. Create some ads first!")
                return
            
            # Create basic analytics message
            total_slots = len(slots)
            active_slots = sum(1 for slot in slots if slot.get('is_active'))
            
            # Get destinations for each slot
            total_destinations = 0
            for slot in slots:
                slot_destinations = await db.get_destinations_for_slot(slot.get('id'))
                total_destinations += len(slot_destinations) if slot_destinations else 0
        except Exception as slot_err:
            logger.error(f"Error getting user slots: {slot_err}")
            await update.message.reply_text("❌ Error loading ad slots. Please try again.")
            return
        
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
            InlineKeyboardButton("🥉 Basic - $15", callback_data="subscribe:basic"),
            InlineKeyboardButton("🥈 Pro - $45", callback_data="subscribe:pro")
        ],
        [
            InlineKeyboardButton("🥇 Enterprise - $75", callback_data="subscribe:enterprise")
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
        f"🚀 **AutoFarming Pro - Automated Telegram Advertising**\n\n"
        f"{status_text}\n\n"
        "**📢 What You Get:**\n"
        "✅ **Automated posting** to multiple Telegram groups\n"
        "✅ **Custom scheduling** (post every 1-24 hours)\n"
        "✅ **Multi-group management** (post to many groups at once)\n"
        "✅ **Content management** (text, photos, videos)\n"
        "✅ **Real-time analytics** and performance tracking\n\n"
        "**💎 Choose your plan:**\n\n"
        "**🥉 Basic Plan - $15/month**\n"
        "• **1 advertising campaign** (ad slot)\n"
        "• **Post to up to 10 groups** per campaign\n"
        "• **Perfect for:** Small businesses, personal promotion\n\n"
        "**🥈 Pro Plan - $45/month**\n"
        "• **3 advertising campaigns** (ad slots)\n"
        "• **Post to up to 30 groups total** (10 per campaign)\n"
        "• **Perfect for:** Growing businesses, multiple products\n\n"
        "**🥇 Enterprise Plan - $75/month**\n"
        "• **5 advertising campaigns** (ad slots)\n"
        "• **Post to up to 50 groups total** (10 per campaign)\n"
        "• **Perfect for:** Large businesses, agencies, marketers\n\n"
        "**⏰ All plans include:**\n"
        "• 30-day subscription period\n"
        "• Multi-cryptocurrency payment support\n"
        "• 24/7 automated posting\n"
        "• Professional customer support\n\n"
        "**📈 Example:** With Basic plan, you can create 1 campaign to automatically post your business ads to 10 different Telegram groups every 2 hours!\n\n"
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
        # Go directly to crypto selection - no duplicate menu
        await show_crypto_selection(update, context, tier)
    
    elif query.data.startswith("pay:"):
        # Handle new payment format: pay:{tier}
        tier = query.data.split(":")[1]
        await show_crypto_selection(update, context, tier)
    
    elif query.data.startswith("crypto:"):
        # Handle crypto selection: crypto:{tier}:{crypto_type}
        parts = query.data.split(":")
        if len(parts) == 3:
            tier = parts[1]
            crypto_type = parts[2]
            await handle_crypto_selection(update, context, tier, crypto_type)
    
    elif query.data.startswith("check_payment:"):
        # Handle payment status check
        payment_id = query.data.split(":")[1]
        await check_payment_status_callback(update, context, payment_id)
    
    elif query.data.startswith("cancel_payment:"):
        # Handle payment cancellation
        payment_id = query.data.split(":")[1]
        await cancel_payment_callback(update, context, payment_id)
    
    elif query.data.startswith("copy_address:"):
        # Handle address copy
        crypto_type = query.data.split(":")[1]
        await copy_address_callback(update, context, crypto_type)
    
    elif query.data == "compare_plans":
        await compare_plans_callback(update, context)
    elif query.data == "back_to_plans":
        await subscribe_callback(update, context)
    elif query.data.startswith("slot_analytics:"):
        slot_id = query.data.split(":")[1]
        await slot_analytics_callback(update, context, slot_id)
    elif query.data.startswith("category:"):
        # Handle category selection: category:{slot_id}:{category}
        parts = query.data.split(":")
        if len(parts) == 3:
            slot_id = parts[1]
            category = parts[2]
            await handle_category_selection(update, context, slot_id, category)

async def show_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str):
    """Show cryptocurrency selection interface."""
    query = update.callback_query
    
    try:
        # Define supported cryptocurrencies directly (no price fetching)
        cryptos = {
            'BTC': {'symbol': 'BTC', 'name': 'Bitcoin'},
            'ETH': {'symbol': 'ETH', 'name': 'Ethereum'},
            'USDT': {'symbol': 'USDT', 'name': 'Tether USD'},
            'USDC': {'symbol': 'USDC', 'name': 'USD Coin'},
            'TON': {'symbol': 'TON', 'name': 'Toncoin'}
        }
        
        # Create crypto selection keyboard (without prices)
        keyboard = []
        for crypto_type, crypto_data in cryptos.items():
            button_text = f"{crypto_data['symbol']}"
            callback_data = f"crypto:{tier}:{crypto_type}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Plans", callback_data="cmd:subscribe")])
        
        message_text = (
            f"💎 **Choose Payment Method**\n\n"
            f"**Selected Plan:** {tier.title()}\n\n"
            "Select your preferred cryptocurrency:\n\n"
            "*All payments are processed securely*"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Error showing crypto selection: {e}")
        await query.edit_message_text(
            "❌ Error loading payment options. Please try again.",
            parse_mode='Markdown'
        )

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, slot_id: str, category: str):
    """Handle category selection for ad slot."""
    query = update.callback_query
    
    try:
        # Update the ad slot with the selected category
        db = context.bot_data['db']
        success = await db.update_slot_category(int(slot_id), category)
        
        if success:
            # Store the slot_id in user_data for the conversation
            context.user_data['current_slot_id'] = int(slot_id)
            
            # Show content input prompt
            await query.edit_message_text(
                f"📝 **Set Ad Content**\n\n"
                f"Category: **{category.title()}**\n\n"
                f"Please send me the content for your ad.\n\n"
                f"You can send:\n"
                f"• Text message\n"
                f"• Photo with caption\n"
                f"• Video with caption\n\n"
                f"Use /cancel to go back.",
                parse_mode='Markdown'
            )
            # Note: This function is called from the main callback handler, 
            # not from within a conversation, so we can't return a conversation state here
        else:
            await query.edit_message_text(
                "❌ Error setting category. Please try again.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        context.bot_data['logger'].error(f"Error handling category selection: {e}")
        await query.edit_message_text(
            "❌ Error setting category. Please try again."
        )

async def send_payment_qr_code(query, crypto_type: str, payment_request: dict) -> bool:
    """Generate and send a QR code for the payment."""
    try:
        import qrcode
        from io import BytesIO
        
        # Create QR code data based on crypto type
        if crypto_type == 'TON':
            # TON deep link with amount and comment
            amount_nano = int(payment_request['amount_crypto'] * 1e9)
            address = payment_request.get('pay_to_address', '')
            comment = payment_request.get('payment_memo', payment_request['payment_id'])
            qr_data = f"ton://transfer/{address}?amount={amount_nano}&text={comment}"
        elif crypto_type == 'BTC':
            # Bitcoin URI with amount
            address = payment_request.get('pay_to_address', '')
            amount = payment_request['amount_crypto']
            qr_data = f"bitcoin:{address}?amount={amount:.8f}"
        else:
            # Generic address for other cryptos
            qr_data = payment_request.get('pay_to_address', '')
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        qr_bytes = BytesIO()
        qr_image.save(qr_bytes, format='PNG')
        qr_bytes.seek(0)
        
        # Send QR code as photo
        await query.message.reply_photo(
            photo=qr_bytes,
            caption=f"🔗 {crypto_type} Payment QR Code\n\nScan with your {crypto_type} wallet app"
        )
        
        return True
        
    except Exception as e:
        print(f"QR code generation error: {e}")
        return False

async def handle_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str, crypto_type: str):
    """Handle cryptocurrency selection and create payment."""
    query = update.callback_query
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    try:
        # Get current subscription status
        subscription = await db.get_user_subscription(user_id)
        if subscription and subscription['is_active']:
            await query.edit_message_text(
                "❌ You already have an active subscription.\n\n"
                "Use /my_ads to manage your existing ad slots."
            )
            return
        
        # Create payment request
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        payment_request = await payment_processor.create_payment_request(
            user_id=user_id,
            tier=tier,
            crypto_type=crypto_type
        )
        
        if payment_request.get('error'):
            await query.edit_message_text(f"❌ Error creating payment: {payment_request['error']}")
            return
        
        # Create user-friendly keyboard with essential actions
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ I've Sent the Payment", 
                    callback_data=f"check_payment:{payment_request['payment_id']}"
                )
            ],
            [
                InlineKeyboardButton("📋 Copy Address", callback_data=f"copy_address:{crypto_type}"),
                InlineKeyboardButton("🔄 Check Status", callback_data=f"check_payment:{payment_request['payment_id']}")
            ],
            [
                InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_payment:{payment_request['payment_id']}"),
                InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")
            ]
        ]

        # Create a user-friendly payment interface
        amount_crypto = payment_request.get('amount_crypto', 0)
        amount_usd = payment_request.get('amount_usd', 0)
        payment_id = str(payment_request.get('payment_id', 'N/A'))
        
        # Generate QR code for the payment
        qr_code_sent = False
        try:
            qr_code_sent = await send_payment_qr_code(query, crypto_type, payment_request)
        except Exception as qr_error:
            context.bot_data['logger'].warning(f"QR code generation failed: {qr_error}")
        
        # Create simplified text instructions
        if crypto_type == 'TON':
            pay_to_address = str(payment_request.get('pay_to_address', 'N/A'))
            payment_memo = str(payment_request.get('payment_memo', payment_id))
            
            text = (
                f"💎 TON Payment\n"
                f"Plan: {tier.title()}\n"
                f"Amount: {amount_crypto:.6f} TON (${amount_usd})\n\n"
                f"📍 Send to: {pay_to_address}\n"
                f"💬 Include comment: {payment_memo}\n\n"
                f"⚠️ The comment is REQUIRED to identify your payment!\n\n"
                f"📱 Use your TON wallet app to scan the QR code above or copy the address manually."
            )
        elif crypto_type == 'BTC':
            pay_to_address = str(payment_request.get('pay_to_address', 'N/A'))
            
            text = (
                f"₿ Bitcoin Payment\n"
                f"Plan: {tier.title()}\n"
                f"Amount: {amount_crypto:.8f} BTC (${amount_usd})\n\n"
                f"📍 Send to: {pay_to_address}\n\n"
                f"📱 Use your Bitcoin wallet app to scan the QR code above or copy the address manually."
            )
        
        # Debug: Log the text length and content for troubleshooting
        context.bot_data['logger'].info(f"Payment text length: {len(text)}, crypto: {crypto_type}, tier: {tier}")
        
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as text_error:
            # If text parsing fails, send a simplified message
            context.bot_data['logger'].error(f"Text parsing failed: {text_error}, trying simplified message")
            simplified_text = f"💳 {crypto_type} Payment for {tier.title()}\n\nAmount: {amount_crypto:.6f} {crypto_type}\nPayment ID: {payment_id}\n\nUse the button below to proceed with payment."
            await query.edit_message_text(simplified_text, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        context.bot_data['logger'].error(f"Error in handle_crypto_selection: {e}")
        await query.edit_message_text(f"❌ Error creating payment: {str(e)}")

async def handle_crypto_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crypto selection callbacks like crypto:basic:TON."""
    query = update.callback_query
    data = query.data
    
    try:
        # Parse callback data: crypto:tier:crypto_type
        parts = data.split(":")
        if len(parts) != 3:
            await query.answer("Invalid selection")
            return
            
        _, tier, crypto_type = parts
        
        # Call the existing handle_crypto_selection function
        await handle_crypto_selection(update, context, tier, crypto_type)
        
    except Exception as e:
        context.bot_data['logger'].error(f"Error in handle_crypto_selection_callback: {e}")
        await query.edit_message_text("❌ Error processing selection")

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str):
    """Handle payment button clicks for new payment system."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Show cryptocurrency selection first
    await show_crypto_selection(update, context, tier)
    
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
        # Get payment status using multi-crypto processor
        from multi_crypto_payments import MultiCryptoPaymentProcessor
        payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        # Get payment status
        status = await payment_processor.get_payment_status(payment_id)
        
        if status['status'] == 'not_found':
            await query.edit_message_text(f"❌ Payment not found: {status.get('message')}")
            return
        
        if status['status'] == 'error':
            await query.edit_message_text(f"❌ Error checking payment: {status.get('message')}")
            return
        
        if status['status'] == 'completed':
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
        elif status['status'] == 'pending':
            # Check if payment has been received
            verification = await payment_processor.verify_payment_on_blockchain(payment_id)
            
            if verification:
                # Payment verified - subscription is automatically activated
                keyboard = [
                    [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")],
                    [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                ]
                text = (
                    "🎉 **Payment Verified!**\n\n"
                    f"✅ Subscription activated successfully!\n"
                    f"🆔 Payment ID: `{payment_id}`\n\n"
                    "You can now use your ad slots!"
                )
            else:
                # Payment still pending
                from datetime import datetime
                check_time = datetime.now().strftime("%H:%M:%S")
                keyboard = [
                    [InlineKeyboardButton("🔄 Check Again", callback_data=f"check_payment:{payment_id}")],
                    [InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_payment:{payment_id}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
                ]
                text = (
                    "⏳ **Payment Pending**\n\n"
                    f"We're still waiting for your payment.\n"
                    f"Payment ID: `{payment_id}`\n"
                    f"Last checked: {check_time}\n\n"
                    "Please ensure you sent the correct amount.\n"
                    "Click 'Check Again' in 30 seconds."
                )
        elif status['status'] == 'expired':
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data="cmd:subscribe")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                "⏰ **Payment Expired**\n\n"
                f"Payment ID: `{payment_id}`\n\n"
                "Please create a new payment request."
            )
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Create New Payment", callback_data="cmd:subscribe")],
                [InlineKeyboardButton("🔙 Back", callback_data="cmd:subscribe")]
            ]
            text = (
                f"❓ **Payment Status: {status['status']}**\n\n"
                f"Payment ID: `{payment_id}`\n\n"
                "Please contact support for assistance."
            )
        
        # Remove markdown formatting to avoid parsing issues
        clean_text = text.replace("**", "").replace("`", "")
        await query.edit_message_text(clean_text, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in check_payment_status_callback: {e}")
        await query.edit_message_text(f"❌ Error checking payment: {str(e)}")

async def cancel_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    """Cancel a pending payment."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        db = context.bot_data['db']
        
        # Update payment status to cancelled
        success = await db.update_payment_status(payment_id, 'cancelled')
        
        if success:
            await query.edit_message_text(
                f"❌ Payment Cancelled\n\n"
                f"Payment ID: {payment_id}\n\n"
                f"You can create a new payment anytime.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 New Payment", callback_data="cmd:subscribe")],
                    [InlineKeyboardButton("📊 My Status", callback_data="cmd:status")]
                ])
            )
        else:
            await query.edit_message_text(
                f"❌ Could not cancel payment\n\n"
                f"Payment ID: {payment_id}\n\n"
                f"Please try again or contact support."
            )
    
    except Exception as e:
        logger.error(f"Error in cancel_payment_callback: {e}")
        await query.edit_message_text(f"❌ Error cancelling payment: {str(e)}")

async def copy_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_type: str):
    """Show copyable address for manual payment."""
    import os
    query = update.callback_query
    
    try:
        # Get the configured address for the crypto type
        config = context.bot_data['config']
        
        if crypto_type == 'TON':
            address = getattr(config, 'ton_address', '') or os.getenv('TON_ADDRESS', '')
            network_name = "TON Network"
        elif crypto_type == 'BTC':
            address = getattr(config, 'btc_address', '') or os.getenv('BTC_ADDRESS', '')
            network_name = "Bitcoin Network"
        else:
            address = "Address not configured"
            network_name = crypto_type
        
        if address:
            await query.answer(
                f"📋 {crypto_type} Address:\n{address}\n\nTap and hold to copy!",
                show_alert=True
            )
        else:
            await query.answer(
                f"❌ {crypto_type} address not configured",
                show_alert=True
            )
    
    except Exception as e:
        logger.error(f"Error in copy_address_callback: {e}")
        await query.answer("❌ Error getting address", show_alert=True)

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
            
            # Use the new multi-crypto payment processor
            from multi_crypto_payments import MultiCryptoPaymentProcessor
            payment_processor = MultiCryptoPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
            
            # Verify payment on blockchain
            is_verified = await payment_processor.verify_payment_on_blockchain(payment)
            
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
    """Show user status and subscription information."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    config = context.bot_data.get('config')
    is_admin = False
    try:
        is_admin = config.is_admin(user_id) if config else False
    except Exception:
        is_admin = False
    
    subscription = await db.get_user_subscription(user_id)
    logger.info(f"Status check - User {user_id} subscription: {subscription}")
    
    if subscription and subscription.get('is_active'):
        status_text = f"✅ **Active Subscription:** {subscription['tier'].title()}"
    else:
        status_text = "❌ **No active subscription**"
        if subscription:
            status_text += f"\n📋 **Subscription Data:** {subscription}"
    
    message = (
        f"📊 **Your Status**\n\n"
        f"**User ID:** `{user_id}`\n"
        f"{status_text}"
    )
    if is_admin:
        message += (
            "\n\n"
            "💡 **Admin hint**\n"
            "Set in .env if needed:\n"
            f"`ADMIN_ID={user_id}`"
        )
    await update.message.reply_text(message, parse_mode='Markdown')

# --- Main Ad Management Command ---

async def my_ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's ad slots."""
    try:
        db = context.bot_data['db']
        user_id = update.effective_user.id
        config = context.bot_data.get('config')

        # Check if user is admin
        is_admin = config.is_admin(user_id) if config else False
        
        # Create user if they don't exist
        user = await db.get_user(user_id)
        if not user:
            await db.create_user(
                user_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            )

        # If admin, show admin slots instead of regular slots
        if is_admin:
            await show_admin_ads_interface(update, context)
            return

        subscription = await db.get_user_subscription(user_id)
        logger.info(f"User {user_id} subscription: {subscription}")
        
        if not subscription or not subscription.get('is_active'):
            reply_obj = update.message if update.message else update.callback_query.message
            await reply_obj.reply_text(
                "❌ You need an active subscription to manage ads.\n\n"
                "Please contact the admin to get a subscription."
            )
            return

        ad_slots = await db.get_or_create_ad_slots(user_id, subscription['tier'])
        logger.info(f"User {user_id} ad slots: {ad_slots}")
        
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

async def show_admin_ads_interface(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin-specific ads interface."""
    try:
        db = context.bot_data['db']
        
        # Get admin slots
        admin_slots = await db.get_admin_ad_slots()
        
        if not admin_slots:
            # Create initial admin slots if none exist
            await db.create_admin_ad_slots()
            admin_slots = await db.get_admin_ad_slots()
        
        message_text = "🎯 **Admin Ad Slots**\n\n"
        message_text += f"**Total Slots:** {len(admin_slots)} (Unlimited)\n"
        message_text += "**Purpose:** Promotional content and announcements\n\n"
        message_text += "Select a slot to manage:"
        
        keyboard = []
        
        # Create slot buttons (5 per row)
        for i in range(0, len(admin_slots), 5):
            row = []
            for j in range(5):
                if i + j < len(admin_slots):
                    slot = admin_slots[i + j]
                    slot_number = slot['slot_number']
                    status = "✅" if slot['is_active'] else "⏸️"
                    row.append(InlineKeyboardButton(
                        f"{status} {slot_number}", 
                        callback_data=f"admin_slot:{slot_number}"
                    ))
            keyboard.append(row)
        
        # Add management buttons
        keyboard.append([
            InlineKeyboardButton("📝 Quick Post", callback_data="admin_quick_post"),
            InlineKeyboardButton("📊 Slot Stats", callback_data="admin_slot_stats")
        ])
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_slots_refresh"),
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in show_admin_ads_interface: {e}")
        error_message = "❌ Error loading admin slots. Please try again."
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

    # Show category selection first
    keyboard = [
        [InlineKeyboardButton("💎 Crypto/Finance", callback_data=f"category:{slot_id}:crypto")],
        [InlineKeyboardButton("💻 Tech/Software", callback_data=f"category:{slot_id}:tech")],
        [InlineKeyboardButton("🏢 Business/General", callback_data=f"category:{slot_id}:business")],
        [InlineKeyboardButton("🎯 Marketing/Promotion", callback_data=f"category:{slot_id}:marketing")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"slot:{slot_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 **Set Ad Content**\n\n"
        "First, select the category for your ad:\n\n"
        "**💎 Crypto/Finance** - Cryptocurrency, trading, financial services\n"
        "**💻 Tech/Software** - Software, apps, technology services\n"
        "**🏢 Business/General** - General business, services, products\n"
        "**🎯 Marketing/Promotion** - Promotional content, offers, deals\n\n"
        "Choose a category:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SETTING_AD_CONTENT

async def handle_content_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection within the content conversation."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse callback data: category:{slot_id}:{category}
        parts = query.data.split(":")
        if len(parts) != 3:
            await query.edit_message_text("❌ Invalid category selection. Please try again.")
            return ConversationHandler.END
        
        slot_id = int(parts[1])
        category = parts[2]
        
        # Update the ad slot with the selected category
        db = context.bot_data['db']
        success = await db.update_slot_category(slot_id, category)
        
        if success:
            # Store the slot_id in user_data for the conversation
            context.user_data['current_slot_id'] = slot_id
            
            # Show content input prompt
            await query.edit_message_text(
                f"📝 **Set Ad Content**\n\n"
                f"Category: **{category.title()}**\n\n"
                f"Please send me the content for your ad.\n\n"
                f"You can send:\n"
                f"• Text message\n"
                f"• Photo with caption\n"
                f"• Video with caption\n\n"
                f"Use /cancel to go back.",
                parse_mode='Markdown'
            )
            # Continue in the same conversation state to receive the content
            return SETTING_AD_CONTENT
        else:
            await query.edit_message_text(
                "❌ Error setting category. Please try again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
    except Exception as e:
        context.bot_data['logger'].error(f"Error handling content category selection: {e}")
        await query.edit_message_text(
            "❌ Error setting category. Please try again."
        )
        return ConversationHandler.END

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

    # Provide a clear confirmation with navigation
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to This Slot", callback_data=f"slot:{slot_id}")],
        [InlineKeyboardButton("🔙 Back to My Ads", callback_data="cmd:my_ads")]
    ]
    if success:
        await update.message.reply_text(
            "✅ Your ad content has been saved successfully!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            "❌ An error occurred while saving your ad.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    context.user_data.pop('current_slot_id', None)
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
        "Enter the interval in minutes (60-1440):\n\n"
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
        
        if interval < 60:
            await update.message.reply_text("❌ Minimum interval is 60 minutes. Please try again.")
            return SETTING_AD_SCHEDULE
        elif interval > 1440:
            await update.message.reply_text("❌ Maximum interval is 1440 minutes (24 hours). Please try again.")
            return SETTING_AD_SCHEDULE

        success = await db.update_ad_slot_schedule(slot_id, interval)

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

        keyboard = [
            [InlineKeyboardButton("⬅️ Back to This Slot", callback_data=f"slot:{slot_id}")],
            [InlineKeyboardButton("🔙 Back to My Ads", callback_data="cmd:my_ads")]
        ]

        if success:
            await update.message.reply_text(
                f"✅ Schedule saved! Your ad will be posted every {time_str}.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                "❌ An error occurred while saving the schedule.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number. Use /cancel to go back.")
        return SETTING_AD_SCHEDULE

    context.user_data.pop('current_slot_id', None)
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

    # Create category selection keyboard with emojis and 2 columns
    emoji_map = {
        'exchange services': '💱', 'telegram': '📣', 'discord': '💬', 'instagram': '📸',
        'x/twitter': '𝕏', 'tiktok': '🎵', 'facebook': '📘', 'youtube': '▶️', 'steam': '🎮',
        'twitch': '🟣', 'telegram gifts': '🎁', 'other social media': '🌐',
        'gaming accounts': '🕹️', 'gaming services': '🛠️', 'other services': '🧩',
        'other accounts': '👥', 'meme coins': '🪙', 'usernames': '🔤', 'gaming currencies': '💰',
        'bots and tools': '🤖', 'account upgrade': '⬆️'
    }
    keyboard = []
    row = []
    for category in sorted(categories):
        category_groups = [g for g in all_groups if g['category'] == category]
        label = f"{emoji_map.get(category, '📋')} {category.title()} ({len(category_groups)})"
        row.append(InlineKeyboardButton(label, callback_data=f"select_category:{slot_id}:{category}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
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
    
    # Set destinations for this slot: expect list of dicts
    destinations = [
        {
            'destination_type': 'chat',
            'destination_id': group.get('group_id') or group.get('group_name'),
            'destination_name': group.get('group_name'),
            'alias': None,
        }
        for group in category_groups
    ]
    success = await db.update_destinations_for_slot(slot_id, destinations)
    
    if success:
        await query.edit_message_text(
            f"✅ **Destinations Changed Successfully!**\n\n"
            f"**Category:** {category.title()}\n"
            f"**Groups:** {len(destinations)} groups\n\n"
            f"🔄 **Bot restarted for your ads**\n"
            f"Your ads will now be posted to all {category} groups automatically.\n\n"
            f"⏱️ **Brief pause applied** to ensure clean transition.",
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
        # Get user slots for basic analytics
        slots = await db.get_or_create_ad_slots(user_id, subscription.get('tier', 'basic'))
        if not slots:
            await query.edit_message_text("❌ No ad slots found. Create some ads first!")
            return
        
        # Create basic analytics message
        total_slots = len(slots)
        active_slots = sum(1 for slot in slots if slot.get('is_active'))
        
        # Get destinations for each slot
        total_destinations = 0
        for slot in slots:
            slot_destinations = await db.get_destinations_for_slot(slot.get('id'))
            total_destinations += len(slot_destinations) if slot_destinations else 0
        
        # Calculate days remaining
        days_remaining = 0
        if subscription.get('expires'):
            from datetime import datetime
            expires_value = subscription['expires']
            if isinstance(expires_value, str):
                try:
                    expires_dt = datetime.fromisoformat(expires_value)
                except Exception:
                    try:
                        from datetime import datetime as _dt
                        expires_dt = _dt.strptime(expires_value, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        expires_dt = datetime.now()
            else:
                expires_dt = expires_value
            days_remaining = max(0, (expires_dt - datetime.now()).days)
        
        # Create analytics message
        message = f"""📊 **Your Analytics**

🎯 **Ad Slots:** {total_slots} total, {active_slots} active
📍 **Destinations:** {total_destinations} total
⏰ **Subscription:** {subscription.get('tier', 'Unknown').title()}
📅 **Days Remaining:** {days_remaining}

*More detailed analytics coming soon!*"""
        
        # Add back button
        keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="cmd:start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        await query.edit_message_text("❌ Error loading analytics. Please try again later.")

async def referral_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral code and statistics (callback version)."""
    query = update.callback_query
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    try:
        # Simple referral code generation (hash-based)
        import hashlib
        referral_code = hashlib.md5(f"user_{user_id}".encode()).hexdigest()[:8].upper()
        
        # Basic referral statistics (placeholder)
        stats = {
            'total_referrals': 0,
            'pending_referrals': 0,
            'rewards_earned': 0
        }
        
        # Create referral message
        message = f"""
🎁 Your Referral Program

🔗 Your Referral Code:
`{referral_code}`

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
    
    # Use the same logic as the main subscribe function
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    # Get current subscription status
    subscription = await db.get_user_subscription(user_id)
    
    # Create enhanced subscription plans keyboard
    keyboard = [
        [
            InlineKeyboardButton("🥉 Basic - $15", callback_data="subscribe:basic"),
            InlineKeyboardButton("🥈 Pro - $45", callback_data="subscribe:pro")
        ],
        [
            InlineKeyboardButton("🥇 Enterprise - $75", callback_data="subscribe:enterprise")
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
        f"🚀 **AutoFarming Pro - Automated Telegram Advertising**\n\n"
        f"{status_text}\n\n"
        "**📢 What You Get:**\n"
        "✅ **Automated posting** to multiple Telegram groups\n"
        "✅ **Custom scheduling** (post every 1-24 hours)\n"
        "✅ **Multi-group management** (post to many groups at once)\n"
        "✅ **Content management** (text, photos, videos)\n"
        "✅ **Real-time analytics** and performance tracking\n\n"
        "**💎 Choose your plan:**\n\n"
        "**🥉 Basic Plan - $15/month**\n"
        "• **1 advertising campaign** (ad slot)\n"
        "• **Post to up to 10 groups** per campaign\n"
        "• **Perfect for:** Small businesses, personal promotion\n\n"
        "**🥈 Pro Plan - $45/month**\n"
        "• **3 advertising campaigns** (ad slots)\n"
        "• **Post to up to 30 groups total** (10 per campaign)\n"
        "• **Perfect for:** Growing businesses, multiple products\n\n"
        "**🥇 Enterprise Plan - $75/month**\n"
        "• **5 advertising campaigns** (ad slots)\n"
        "• **Post to up to 50 groups total** (10 per campaign)\n"
        "• **Perfect for:** Large businesses, agencies, marketers\n\n"
        "**⏰ All plans include:**\n"
        "• 30-day subscription period\n"
        "• Multi-cryptocurrency payment support\n"
        "• 24/7 automated posting\n"
        "• Professional customer support\n\n"
        "**📈 Example:** With Basic plan, you can create 1 campaign to automatically post your business ads to 10 different Telegram groups every 2 hours!\n\n"
        "Select a plan to proceed with payment:"
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

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
        "🥉 **Basic Plan - $15/month**\n"
        "• 1 ad slot\n"
        "• 10 destinations per slot\n"
        "• Basic analytics\n"
        "• Email support\n"
        "• Standard posting\n\n"
        "🥈 **Pro Plan - $45/month**\n"
        "• 3 ad slots\n"
        "• 10 destinations per slot\n"
        "• Advanced analytics\n"
        "• Priority support\n"
        "• Custom scheduling\n"
        "• Ban protection\n\n"
        "🥇 **Enterprise Plan - $75/month**\n"
        "• 5 ad slots\n"
        "• 10 destinations per slot\n"
        "• Full analytics suite\n"
        "• 24/7 support\n"
        "• Auto-renewal\n"
        "• Premium features\n\n"
        "💡 *All plans include 30-day duration and multi-crypto payment support*"
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