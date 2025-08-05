from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin."""
    config = context.bot_data['config']
    user_id = update.effective_user.id
    return config.is_admin(user_id)

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new group to the managed groups list."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add_group <group_id> <group_name> [category]\n"
            "Example: /add_group -1001234567890 'My Group' general"
        )
        return
    
    try:
        group_id = context.args[0]
        group_name = context.args[1]
        category = context.args[2] if len(context.args) > 2 else "general"
        
        db = context.bot_data['db']
        success = await db.add_managed_group(group_id, group_name, category)
        
        if success:
            await update.message.reply_text(f"✅ Group '{group_name}' added successfully!")
        else:
            await update.message.reply_text("❌ Failed to add group. Please try again.")
            
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text("❌ Error adding group. Please check the format.")

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all managed groups."""
    try:
        db = context.bot_data['db']
        groups = await db.get_managed_groups()
        
        if not groups:
            await update.message.reply_text("📋 No managed groups found.")
            return
        
        text = "📋 **Managed Groups:**\n\n"
        for group in groups:
            text += f"**{group['group_name']}**\n"
            text += f"• ID: `{group['group_id']}`\n"
            text += f"• Category: {group['category']}\n"
            text += f"• Status: {'✅ Active' if group['is_active'] else '❌ Inactive'}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        await update.message.reply_text("❌ Error listing groups.")

async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a group from the managed groups list."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /remove_group <group_name>\n"
            "Example: /remove_group 'My Group'"
        )
        return
    
    try:
        group_name = " ".join(context.args)
        db = context.bot_data['db']
        success = await db.remove_managed_group(group_name)
        
        if success:
            await update.message.reply_text(f"✅ Group '{group_name}' removed successfully!")
        else:
            await update.message.reply_text("❌ Failed to remove group. Please check the name.")
            
    except Exception as e:
        logger.error(f"Error removing group: {e}")
        await update.message.reply_text("❌ Error removing group.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics."""
    try:
        db = context.bot_data['db']
        stats = await db.get_stats()
        
        text = "📊 **Admin Statistics:**\n\n"
        text += f"👥 **Users:** {stats['total_users']}\n"
        text += f"💎 **Active Subscriptions:** {stats['active_subscriptions']}\n"
        text += f"📨 **Messages Today:** {stats['messages_today']}\n"
        text += f"💰 **Revenue This Month:** ${stats['revenue_this_month']:.2f}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        await update.message.reply_text("❌ Error getting statistics.")

async def posting_service_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show posting service status."""
    try:
        posting_service = context.bot_data.get('posting_service')
        if not posting_service:
            await update.message.reply_text("❌ Posting service not available.")
            return
        
        status = await posting_service.get_service_status()
        
        if 'error' in status:
            await update.message.reply_text(f"❌ Error getting service status: {status['error']}")
            return
        
        service_status = status['service_status']
        statistics = status['statistics']
        components = status['components']
        
        text = "🤖 **Posting Service Status:**\n\n"
        
        # Service status
        text += f"🔄 **Status:** {'✅ Running' if service_status['is_running'] else '❌ Stopped'}\n"
        if service_status['uptime']:
            text += f"⏱️ **Uptime:** {service_status['uptime']}\n"
        if service_status['last_posting_cycle']:
            text += f"📤 **Last Cycle:** {service_status['last_posting_cycle']}\n"
        if service_status['last_cleanup']:
            text += f"🧹 **Last Cleanup:** {service_status['last_cleanup']}\n"
        
        text += f"⏰ **Cycle Interval:** {service_status['posting_cycle_interval']} minutes\n\n"
        
        # Statistics
        text += "📊 **Statistics:**\n"
        text += f"• Total Posts Sent: {statistics['total_posts_sent']}\n"
        text += f"• Total Posts Failed: {statistics['total_posts_failed']}\n"
        text += f"• Pending Ads: {statistics['pending_ads_count']}\n"
        text += f"• Total Cycles: {statistics['cycle_stats']['total_cycles']}\n"
        text += f"• Last Cycle Duration: {statistics['cycle_stats']['last_cycle_duration']:.1f}s\n"
        text += f"• Expired Subscriptions Cleaned: {statistics['cycle_stats']['expired_subscriptions_cleaned']}\n\n"
        
        # Components
        text += "🔧 **Components:**\n"
        text += f"• Worker Manager: {'✅ Available' if components['worker_manager'] else '❌ Not Available'}\n"
        text += f"• Auto Poster: {'✅ Available' if components['auto_poster'] else '❌ Not Available'}\n"
        text += f"• Payment Processor: {components['payment_processor']}\n"
        
        # Anti-ban config
        anti_ban = status['anti_ban_config']
        text += f"\n🛡️ **Anti-Ban Config:**\n"
        text += f"• Min Delay: {anti_ban['min_delay']}s\n"
        text += f"• Max Delay: {anti_ban['max_delay']}s\n"
        text += f"• Max Posts/Cycle: {anti_ban['max_posts_per_cycle']}\n"
        
        # Add control buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Restart Service", callback_data="admin:restart_posting"),
                InlineKeyboardButton("⏸️ Pause Service", callback_data="admin:pause_posting")
            ],
            [
                InlineKeyboardButton("📊 Detailed Stats", callback_data="admin:detailed_stats"),
                InlineKeyboardButton("⚙️ Config", callback_data="admin:service_config")
            ]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error getting posting service status: {e}")
        await update.message.reply_text("❌ Error getting service status.")

async def restart_posting_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the posting service."""
    try:
        posting_service = context.bot_data.get('posting_service')
        if not posting_service:
            await update.callback_query.answer("❌ Posting service not available.")
            return
        
        await update.callback_query.answer("🔄 Restarting posting service...")
        
        # Restart the service
        await posting_service.restart_service()
        
        await update.callback_query.edit_message_text(
            "✅ Posting service restarted successfully!"
        )
        
    except Exception as e:
        logger.error(f"Error restarting posting service: {e}")
        await update.callback_query.answer("❌ Error restarting service.")

async def pause_posting_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause the posting service."""
    try:
        posting_service = context.bot_data.get('posting_service')
        if not posting_service:
            await update.callback_query.answer("❌ Posting service not available.")
            return
        
        if not posting_service.is_running:
            await update.callback_query.answer("⏸️ Service is already paused.")
            return
        
        await update.callback_query.answer("⏸️ Pausing posting service...")
        
        # Stop the service
        await posting_service.stop_service()
        
        await update.callback_query.edit_message_text(
            "⏸️ Posting service paused successfully!"
        )
        
    except Exception as e:
        logger.error(f"Error pausing posting service: {e}")
        await update.callback_query.answer("❌ Error pausing service.")

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify a payment manually."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /verify_payment <payment_id>\n"
            "Example: /verify_payment TON_abc123def456"
        )
        return
    
    try:
        payment_id = context.args[0]
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await update.message.reply_text("❌ Payment processor not available.")
            return
        
        # Verify the payment
        verification = await payment_processor.verify_payment(payment_id)
        
        if verification.get('payment_verified'):
            # Process the payment
            result = await payment_processor.process_successful_payment(payment_id)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ Payment verified and processed!\n"
                    f"User: {result['user_id']}\n"
                    f"Tier: {result['tier']}\n"
                    f"Slots: {result['slots']}"
                )
            else:
                await update.message.reply_text(f"❌ Payment verification failed: {result.get('error')}")
        else:
            await update.message.reply_text("❌ Payment not verified. Please check the payment ID.")
            
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await update.message.reply_text("❌ Error verifying payment.")

async def revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics."""
    try:
        db = context.bot_data['db']
        
        # Get all completed payments
        # Note: This would need to be implemented in the database manager
        # For now, show a placeholder
        text = "💰 **Revenue Statistics:**\n\n"
        text += "📊 Revenue tracking coming soon!\n"
        text += "This will show:\n"
        text += "• Total revenue\n"
        text += "• Revenue by period\n"
        text += "• Revenue by plan\n"
        text += "• Payment success rates\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        await update.message.reply_text("❌ Error getting revenue statistics.")

async def pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending payments."""
    try:
        db = context.bot_data['db']
        payment_processor = context.bot_data.get('payment_processor')
        
        if not payment_processor:
            await update.message.reply_text("❌ Payment processor not available.")
            return
        
        # Get pending payments
        pending_payments = await db.get_pending_payments(30)  # Last 30 minutes
        
        if not pending_payments:
            await update.message.reply_text("📋 No pending payments found.")
            return
        
        text = "⏳ **Pending Payments:**\n\n"
        for payment in pending_payments:
            text += f"**Payment ID:** `{payment['payment_id']}`\n"
            text += f"**User:** {payment['user_id']}\n"
            text += f"**Amount:** {payment['amount']} {payment['currency']}\n"
            text += f"**Created:** {payment['created_at']}\n"
            text += f"**Expires:** {payment['expires_at']}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting pending payments: {e}")
        await update.message.reply_text("❌ Error getting pending payments.")