from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging

logger = logging.getLogger(__name__)

# --- Define states for our conversations ---
SETTING_AD_CONTENT = 0
SETTING_AD_SCHEDULE = 1
SETTING_AD_DESTINATIONS = 2

# --- Basic Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts the bot."""
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
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle command button callbacks."""
    query = update.callback_query
    await query.answer()
    
    command = query.data.split(":")[1]
    
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows help information."""
    help_text = (
        "📚 *Available Commands:*\n\n"
        "/start \\- Welcome message with buttons\n"
        "/my\\_ads \\- Manage your ad campaigns\n"
        "/analytics \\- View your ad performance\n"
        "/referral \\- Get your referral code\n"
        "/subscribe \\- View subscription plans\n"
        "/help \\- Show this help message"
    )
    
    # Create inline keyboard for quick access
    keyboard = [
        [InlineKeyboardButton("📊 Analytics", callback_data="cmd:analytics")],
        [InlineKeyboardButton("🎁 Referral Program", callback_data="cmd:referral")],
        [InlineKeyboardButton("💎 Subscribe", callback_data="cmd:subscribe")],
        [InlineKeyboardButton("📋 My Ads", callback_data="cmd:my_ads")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, parse_mode='MarkdownV2', reply_markup=reply_markup)

async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user analytics and performance metrics."""
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    # Check if user has active subscription
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await update.message.reply_text(
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
            await update.message.reply_text("❌ No analytics data available yet.")
            return
        
        # Create analytics message
        message = f"""
📊 **Your Analytics (Last 30 Days)**

📈 **Performance:**
• Total Posts: {stats.get('total_posts', 0)}
• Successful Posts: {stats.get('successful_posts', 0)}
• Success Rate: {stats.get('success_rate', 0)}%

🎯 **Reach:**
• Estimated Reach: {stats.get('estimated_reach', 0):,} people
• Active Ad Slots: {stats.get('active_slots', 0)}/{stats.get('ad_slots', 0)}

💰 **ROI:**
• Subscription Cost: ${stats.get('subscription_cost', 0)}
• Estimated Revenue: ${stats.get('estimated_revenue', 0):.2f}
• ROI: {stats.get('roi_percentage', 0)}%

⏰ **Subscription:**
• Days Remaining: {stats.get('days_remaining', 0)}
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Analytics error: {e}")
        await update.message.reply_text("❌ Error loading analytics. Please try again later.")

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's referral code and statistics."""
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
🎁 **Your Referral Program**

🔗 **Your Referral Code:**
`{referral_code}`

📊 **Statistics:**
• Total Referrals: {stats.get('total_referrals', 0)}
• Pending Referrals: {stats.get('pending_referrals', 0)}
• Rewards Earned: {stats.get('rewards_earned', 0)}

💎 **How It Works:**
• Share your referral code with friends
• When they subscribe, you both get rewards
• You get 7 days free subscription
• They get 50% discount on first month

📱 **Share this message:**
"Join AutoFarming Bot with my referral code: {referral_code}"
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Referral error: {e}")
        await update.message.reply_text("❌ Error loading referral information. Please try again later.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows subscription plans and payment options."""
    db = context.bot_data['db']
    user_id = update.effective_user.id
    
    # Get current subscription status
    subscription = await db.get_user_subscription(user_id)
    
    # Create subscription plans keyboard
    keyboard = [
        [InlineKeyboardButton("💎 Basic - $9.99/month", callback_data="subscribe:basic")],
        [InlineKeyboardButton("🚀 Pro - $39.99/month", callback_data="subscribe:pro")],
        [InlineKeyboardButton("🏢 Enterprise - $99.99/month", callback_data="subscribe:enterprise")]
    ]
    
    if subscription and subscription['is_active']:
        status_text = f"✅ **Current Plan:** {subscription['tier'].title()}\n📅 **Expires:** {subscription['expires'].strftime('%Y-%m-%d')}"
    else:
        status_text = "❌ **No active subscription**"
    
    message_text = (
        f"💳 **Subscription Plans**\n\n"
        f"{status_text}\n\n"
        "**Choose your plan:**\n"
        "• **Basic** ($9.99): 1 ad slot, 30 days\n"
        "• **Pro** ($39.99): 5 ad slots, 30 days\n"
        "• **Enterprise** ($99.99): 15 ad slots, 30 days\n\n"
        "Select a plan to proceed with payment:"
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription plan selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("subscribe:"):
        tier = query.data.split(":")[1]
        
        # Create TON payment button
        keyboard = [
            [InlineKeyboardButton("💎 Pay with TON", callback_data=f"pay:{tier}:ton")]
        ]
        
        tier_info = context.bot_data['config'].get_tier_info(tier)
        price = tier_info['price']
        
        message_text = (
            f"💳 **{tier.title()} Plan - ${price}**\n\n"
            f"**Features:**\n"
            f"• {tier_info['ad_slots']} ad slot(s)\n"
            f"• {tier_info['duration_days']} days duration\n"
            f"• Automated posting\n"
            f"• Analytics dashboard\n\n"
            "**Payment Method:** TON (The Open Network)\n\n"
            "Click below to generate payment QR code:"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data.startswith("pay:"):
        _, tier, crypto = query.data.split(":")
        await handle_payment_request(update, context, tier, crypto)

async def handle_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str, crypto: str):
    """Handle payment request and generate payment details."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    try:
        # Import TON payment processor
        from ton_payments import TONPaymentProcessor
        payment_processor = TONPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        # Create payment
        payment_data = await payment_processor.create_payment(user_id, tier)
        
        # Generate QR code
        qr_image = await payment_processor.generate_payment_qr(payment_data)
        
        # Create payment message
        amount_ton = payment_data['amount_crypto']
        wallet_address = payment_data['wallet_address']
        payment_memo = payment_data['payment_memo']
        
        message_text = (
            f"💳 **TON Payment Request**\n\n"
            f"**Plan:** {tier.title()}\n"
            f"**Amount:** {amount_ton} TON\n"
            f"**Address:** `{wallet_address}`\n"
            f"**Memo:** `{payment_memo}`\n\n"
            f"⏰ **Expires in 2 hours**\n\n"
            f"Send the exact amount to the address above with the memo included.\n"
            f"💡 *Note: ±5% tolerance allowed for market fluctuations*\n"
            f"Payment will be verified automatically within 30 seconds."
        )
        
        # Send QR code and payment details
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=qr_image,
            caption=message_text,
            parse_mode='Markdown'
        )
        
        # Add payment tracking keyboard
        keyboard = [[InlineKeyboardButton("🔍 Check Payment Status", callback_data=f"check_payment:{payment_data['payment_id']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ Payment request created! Check the QR code above.\n\nUse the button below to check payment status:",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        context.bot_data['logger'].error(f"Payment creation error: {e}")
        await query.edit_message_text("❌ Error creating payment. Please try again later.")

async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check payment status."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("check_payment:"):
        payment_id = query.data.split(":")[1]
        
        try:
            from ton_payments import TONPaymentProcessor
            payment_processor = TONPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
            
            status = await payment_processor.check_payment_status(payment_id)
            
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
        [InlineKeyboardButton("⬅️ Back to All Slots", callback_data="back_to_slots")]
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
        "• Custom scheduling\n\n"
        "Enterprise Plan - $99.99/month\n"
        "• 15 ad slots\n"
        "• Full analytics suite\n"
        "• 24/7 support\n\n"
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