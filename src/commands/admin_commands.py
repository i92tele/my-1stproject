from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to restrict command to admin only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        config = context.bot_data.get('config')
        if not config:
            await update.message.reply_text("? Bot configuration error")
            return
            
        user_id = update.effective_user.id
        if not config.is_admin(user_id):
            await update.message.reply_text("? This command is for administrators only.")
            return
            
        return await func(update, context)
    return wrapper

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    admin_dashboard = context.bot_data['admin']
    await admin_dashboard.show_dashboard(update, context)

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users."""
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    db = context.bot_data['db']
    
    # Get all users
    users = await db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text(f"?? Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"?? **Broadcast Message:**\n\n{message}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"? Broadcast complete!\n"
        f"Success: {success_count}\n"
        f"Failed: {fail_count}"
    )

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    db = context.bot_data['db']
    stats = await db.get_stats()
    
    stats_text = f"""
?? **Bot Statistics:**

?? Total Users: {stats['total_users']}
? Active Subscriptions: {stats['active_subscriptions']}
?? Messages Today: {stats['messages_today']}
?? Revenue This Month: ${stats['revenue_this_month']:.2f}

?? Bot Status: ? Running
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks."""
    query = update.callback_query
    data = query.data
    
    config = context.bot_data['config']
    if not config.is_admin(update.effective_user.id):
        await query.answer("Unauthorized", show_alert=True)
        return
    
    admin_dashboard = context.bot_data['admin']
    
    # Route to appropriate admin function
    if data == "admin:dashboard":
        await admin_dashboard.show_dashboard(update, context)
    elif data == "admin:users":
        await admin_dashboard.user_management(update, context)
    elif data == "admin:revenue":
        await admin_dashboard.revenue_analytics(update, context)
    elif data == "admin:security":
        await admin_dashboard.security_center(update, context)
    elif data == "admin:broadcast":
        await admin_dashboard.broadcast_center(update, context)
    elif data == "admin:refresh":
        await admin_dashboard.show_dashboard(update, context)
        await query.answer("Dashboard refreshed!")
    else:
        await query.answer("Function not implemented yet")