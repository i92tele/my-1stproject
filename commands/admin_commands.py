from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin."""
    config = context.bot_data['config']
    user_id = update.effective_user.id
    return config.is_admin(user_id)

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a group to the managed groups list."""
    if not await check_admin(update, context):
        await update.message.reply_text("⛔ This command is only available to administrators.")
        return
    
    db = context.bot_data['db']
    
    # Parse command arguments
    args = update.message.text.split(maxsplit=2)
    if len(args) < 3:
        await update.message.reply_text(
            "📝 **Usage:** /add_group <category> <group>\n\n"
            "**Examples:**\n"
            "/add_group crypto @cryptotrading\n"
            "/add_group business https://t.me/businessgroup\n"
            "/add_group forex @forexsignals\n\n"
            "**Categories:** crypto, business, forex, etc."
        )
        return
    
    category = args[1].lower()
    group_identifier = args[2]
    
    # Extract group username from the identifier
    if group_identifier.startswith('https://t.me/'):
        group_username = '@' + group_identifier.split('/')[-1]
    elif not group_identifier.startswith('@'):
        group_username = '@' + group_identifier
    else:
        group_username = group_identifier
    
    try:
        success = await db.add_managed_group(
            group_username=group_username,
            category=category
        )
        
        if success:
            await update.message.reply_text(
                f"✅ Successfully added {group_username} to category '{category}'"
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to add group. It may already exist in the database."
            )
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text("❌ An error occurred while adding the group.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all managed groups."""
    if not await check_admin(update, context):
        await update.message.reply_text("⛔ This command is only available to administrators.")
        return
    
    db = context.bot_data['db']
    
    # Parse command arguments
    args = update.message.text.split(maxsplit=1)
    category = args[1].lower() if len(args) > 1 else None
    
    try:
        groups = await db.get_managed_groups(category)
        
        if not groups:
            if category:
                await update.message.reply_text(f"No groups found in category '{category}'")
            else:
                await update.message.reply_text("No managed groups found. Use /add_group to add some.")
            return
        
        # Group by category
        groups_by_category = {}
        for group in groups:
            cat = group['category']
            if cat not in groups_by_category:
                groups_by_category[cat] = []
            groups_by_category[cat].append(group)
        
        # Format the response
        response = "📋 **Managed Groups:**\n\n"
        for cat, cat_groups in sorted(groups_by_category.items()):
            response += f"**{cat.upper()}** ({len(cat_groups)} groups):\n"
            for group in cat_groups[:10]:
                status = "✅" if group['is_active'] else "❌"
                response += f"{status} {group['group_name']}\n"
            if len(cat_groups) > 10:
                response += f"... and {len(cat_groups) - 10} more\n"
            response += "\n"
        
        response += f"**Total:** {len(groups)} groups"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        await update.message.reply_text("❌ An error occurred while fetching groups.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a group from the managed groups list."""
    if not await check_admin(update, context):
        await update.message.reply_text("⛔ This command is only available to administrators.")
        return
    
    db = context.bot_data['db']
    
    # Parse command arguments
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** /remove_group <group>\n\n"
            "**Example:** /remove_group @cryptotrading"
        )
        return
    
    group_username = args[1]
    if not group_username.startswith('@'):
        group_username = '@' + group_username
    
    try:
        success = await db.remove_managed_group(group_username)
        
        if success:
            await update.message.reply_text(f"✅ Successfully removed {group_username}")
        else:
            await update.message.reply_text(f"❌ Group {group_username} not found in database.")
            
    except Exception as e:
        logger.error(f"Error removing group: {e}")
        await update.message.reply_text("❌ An error occurred while removing the group.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    if not await check_admin(update, context):
        await update.message.reply_text("⛔ This command is only available to administrators.")
        return
    
    db = context.bot_data['db']
    
    try:
        stats = await db.get_bot_statistics()
        
        response = (
            "📊 **Bot Statistics:**\n\n"
            f"👥 Total Users: {stats['total_users']}\n"
            f"💳 Active Subscriptions: {stats['active_subscriptions']}\n"
            f"📢 Total Ad Slots: {stats['total_ad_slots']}\n"
            f"✅ Active Ads: {stats['active_ads']}\n"
            f"🌐 Managed Groups: {stats['total_groups']}"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text("❌ An error occurred while fetching statistics.")

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually verify a payment."""
    if not context.bot_data['config'].is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Check if payment ID and transaction hash are provided
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /verify_payment <payment_id> <transaction_hash>\n\n"
            "Example: /verify_payment PAY_ABC123 0x1234567890abcdef..."
        )
        return
    
    payment_id = args[0]
    tx_hash = args[1]
    
    try:
        from ton_payments import TONPaymentProcessor
        payment_processor = TONPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        success = await payment_processor.verify_payment_manually(payment_id, tx_hash)
        
        if success:
            await update.message.reply_text("✅ Payment verified and subscription activated!")
        else:
            await update.message.reply_text("❌ Failed to verify payment. Please check the payment ID and transaction hash.")
            
    except Exception as e:
        context.bot_data['logger'].error(f"Payment verification error: {e}")
        await update.message.reply_text("❌ Error verifying payment. Please try again.")

async def revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view revenue statistics."""
    if not context.bot_data['config'].is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    try:
        from ton_payments import TONPaymentProcessor
        payment_processor = TONPaymentProcessor(context.bot_data['config'], context.bot_data['db'], context.bot_data['logger'])
        
        stats = await payment_processor.get_payment_statistics()
        
        message = f"""
💰 **TON Revenue Statistics**

📊 **Overview:**
• Total Payments: {stats.get('total_payments', 0)}
• Completed Payments: {stats.get('completed_payments', 0)}
• Total Revenue: ${stats.get('total_revenue', 0):.2f}

💎 **Cryptocurrency:** TON (The Open Network)
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Revenue stats error: {e}")
        await update.message.reply_text("❌ Error getting revenue statistics.")

async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending payments."""
    if not context.bot_data['config'].is_admin(update.effective_user.id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    try:
        async with context.bot_data['db'].pool.acquire() as conn:
            pending_payments = await conn.fetch('''
                SELECT payment_id, user_id, tier, amount_crypto, created_at
                FROM payments 
                WHERE status = 'pending' AND cryptocurrency = 'ton' AND expires_at > CURRENT_TIMESTAMP
                ORDER BY created_at DESC
                LIMIT 10
            ''')
        
        if not pending_payments:
            await update.message.reply_text("📭 No pending TON payments found.")
            return
        
        message = "⏳ **Pending TON Payments:**\n\n"
        
        for payment in pending_payments:
            payment_data = dict(payment)
            message += f"• **{payment_data['payment_id'][:8]}** - {payment_data['tier'].title()} - {payment_data['amount_crypto']} TON\n"
            message += f"  User: {payment_data['user_id']} | Created: {payment_data['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        context.bot_data['logger'].error(f"Pending payments error: {e}")
        await update.message.reply_text("❌ Error getting pending payments.")