from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict
import logging

class AdminDashboard:
    """Admin dashboard with basic features."""
    
    def __init__(self, db, config, logger):
        self.db = db
        self.config = config
        self.logger = logger
    
    async def show_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display main admin dashboard."""
        stats = await self.db.get_stats()
        
        dashboard_text = f"""
??? **Admin Dashboard**

**?? Overview**
?? Total Users: {stats['total_users']}
? Active Subscriptions: {stats['active_subscriptions']}
?? Messages Today: {stats['messages_today']}
?? Revenue This Month: ${stats['revenue_this_month']:.2f}

**Quick Actions:**
/broadcast <message> - Send to all users
/stats - View detailed statistics

Use the buttons below to manage the bot:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("?? Users", callback_data="admin:users"),
                InlineKeyboardButton("?? Revenue", callback_data="admin:revenue")
            ],
            [
                InlineKeyboardButton("?? Broadcast", callback_data="admin:broadcast"),
                InlineKeyboardButton("?? Refresh", callback_data="admin:refresh")
            ]
        ]
        
        await update.message.reply_text(
            dashboard_text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Basic user management."""
        users = await self.db.get_all_users()
        
        text = "?? **User Management**\n\n"
        
        for user in users[:10]:  # Show first 10 users
            sub_status = "?" if user.get('subscription_expires') and user['subscription_expires'] > datetime.now() else "?"
            text += f"{sub_status} {user['first_name']} (@{user.get('username', 'N/A')})\n"
            text += f"   ID: `{user['user_id']}`\n\n"
        
        if len(users) > 10:
            text += f"... and {len(users) - 10} more users"
        
        keyboard = [[InlineKeyboardButton("?? Back", callback_data="admin:dashboard")]]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def revenue_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Basic revenue display."""
        stats = await self.db.get_stats()
        
        text = f"""
?? **Revenue Overview**

This Month: ${stats['revenue_this_month']:.2f}
Active Subscriptions: {stats['active_subscriptions']}

*Detailed analytics coming soon!*
"""
        
        keyboard = [[InlineKeyboardButton("?? Back", callback_data="admin:dashboard")]]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def broadcast_center(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message center."""
        text = """
?? **Broadcast Center**

To broadcast a message, use:
`/broadcast Your message here`

The message will be sent to all bot users.
"""
        
        keyboard = [[InlineKeyboardButton("?? Back", callback_data="admin:dashboard")]]
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )