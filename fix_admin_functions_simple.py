#!/usr/bin/env python3
"""
Fix Admin Functions (Simple Version)

This script adds the missing admin functions:
- show_revenue_stats
- show_worker_status

Usage:
    python fix_admin_functions_simple.py
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def fix_admin_commands():
    """Add missing admin command functions."""
    logger.info("🔧 Adding missing admin functions...")
    
    try:
        admin_commands_path = "commands/admin_commands.py"
        
        if not os.path.exists(admin_commands_path):
            logger.error(f"❌ {admin_commands_path} does not exist")
            return False
        
        with open(admin_commands_path, 'r') as file:
            content = file.read()
        
        # Add imports if needed
        if "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup" not in content:
            content = "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\n" + content
        
        if "from telegram.ext import ContextTypes" not in content:
            content = "from telegram.ext import ContextTypes\n" + content
        
        if "import logging" not in content:
            content = "import logging\n" + content
        
        if "logger = logging.getLogger(__name__)" not in content:
            content = content + "\nlogger = logging.getLogger(__name__)\n"
        
        # Add show_revenue_stats function if missing
        if "async def show_revenue_stats" not in content:
            revenue_stats_function = '''
async def show_revenue_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue statistics."""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get database manager
        db = context.bot_data.get('db')
        if not db:
            await query.edit_message_text("Database not available")
            return
        
        # Get revenue stats
        try:
            stats = await db.get_revenue_stats()
        except Exception as e:
            logger.error(f"Error getting revenue stats: {e}")
            stats = {
                'total_revenue': 0,
                'monthly_revenue': 0,
                'weekly_revenue': 0,
                'daily_revenue': 0,
                'active_subscriptions': 0,
                'total_transactions': 0
            }
        
        # Format message
        message = "💰 Revenue Statistics\\n\\n"
        message += f"Total Revenue: ${stats.get('total_revenue', 0):.2f}\\n"
        message += f"This Month: ${stats.get('monthly_revenue', 0):.2f}\\n"
        message += f"This Week: ${stats.get('weekly_revenue', 0):.2f}\\n"
        message += f"Today: ${stats.get('daily_revenue', 0):.2f}\\n\\n"
        
        message += f"Active Subscriptions: {stats.get('active_subscriptions', 0)}\\n"
        message += f"Total Transactions: {stats.get('total_transactions', 0)}\\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing revenue stats: {e}")
        if update.callback_query:
            await update.callback_query.answer("Error getting revenue stats")
            await update.callback_query.edit_message_text(
                f"Error getting revenue stats: {e}\\n\\n"
                "Please try again later or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
                ])
            )
'''
            content += revenue_stats_function
            logger.info("✅ Added show_revenue_stats function")
        
        # Add show_worker_status function if missing
        if "async def show_worker_status" not in content:
            worker_status_function = '''
async def show_worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worker status."""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get database manager
        db = context.bot_data.get('db')
        if not db:
            await query.edit_message_text("Database not available")
            return
        
        # Get available workers
        try:
            workers = await db.get_available_workers()
        except Exception as e:
            logger.error(f"Error getting available workers: {e}")
            workers = []
        
        # Format message
        message = "👷 Worker Status\\n\\n"
        message += f"Total Workers: {len(workers)}\\n\\n"
        
        # Show all workers with their status
        message += "Worker status (ID | hourly/daily):\\n"
        for worker in workers:
            worker_id = worker.get('worker_id', 'N/A')
            hourly_posts = worker.get('hourly_posts', worker.get('hourly_usage', 0))
            daily_posts = worker.get('daily_posts', worker.get('daily_usage', 0))
            hourly_limit = worker.get('hourly_limit', 15)
            daily_limit = worker.get('daily_limit', 100)
            is_active = worker.get('is_active', 1) == 1
            
            status = "✅ Active" if is_active else "❌ Inactive"
            message += f"• {worker_id} | {hourly_posts}/{hourly_limit} h, {daily_posts}/{daily_limit} d - {status}\\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing worker status: {e}")
        if update.callback_query:
            await update.callback_query.answer("Error getting worker status")
            await update.callback_query.edit_message_text(
                f"Error getting worker status: {e}\\n\\n"
                "Please try again later or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
                ])
            )
'''
            content += worker_status_function
            logger.info("✅ Added show_worker_status function")
        
        # Write updated file
        with open(admin_commands_path, 'w') as file:
            file.write(content)
        
        logger.info("✅ Admin functions added successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing admin commands: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 FIXING ADMIN FUNCTIONS (SIMPLE VERSION)")
    logger.info("=" * 60)
    
    # Fix admin commands
    fix_admin_commands()
    
    logger.info("=" * 60)
    logger.info("📊 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ Added missing admin functions")
    logger.info("")
    logger.info("Don't forget to also run:")
    logger.info("    python fix_worker_count.py")
    logger.info("")
    logger.info("Then restart the bot:")
    logger.info("    python start_bot.py")

if __name__ == "__main__":
    main()
