#!/usr/bin/env python3
"""
Fix Admin Functions

This script adds the missing admin functions:
- show_revenue_stats
- show_worker_status

Usage:
    python fix_admin_functions.py
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
        
        # Check for imports
        needs_imports = False
        if "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup" not in content:
            needs_imports = True
        if "from telegram.ext import ContextTypes" not in content:
            needs_imports = True
        
        # Add imports if needed
        if needs_imports:
            import_lines = """
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)
"""
            # Add imports at the top of the file
            if "import" in content[:500]:
                # Find the last import line
                lines = content.split('\n')
                last_import_line = 0
                for i, line in enumerate(lines):
                    if line.startswith('import') or line.startswith('from'):
                        last_import_line = i
                
                # Insert imports after the last import line
                content = '\n'.join(lines[:last_import_line+1]) + import_lines + '\n'.join(lines[last_import_line+1:])
            else:
                # Add imports at the beginning
                content = import_lines + content
        
        # Add missing functions
        new_functions = []
        
        # Check if show_revenue_stats is missing
        if "async def show_revenue_stats" not in content:
            new_functions.append("""
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
""")
        
        # Check if show_worker_status is missing
        if "async def show_worker_status" not in content:
            new_functions.append("""
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
""")
        
        # Add new functions to the end of the file
        if new_functions:
            content += '\n' + '\n'.join(new_functions)
            
            # Write updated file
            with open(admin_commands_path, 'w') as file:
                file.write(content)
            
            logger.info(f"✅ Added {len(new_functions)} missing admin functions")
        else:
            logger.info("✅ All admin functions already exist")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing admin commands: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 FIXING ADMIN FUNCTIONS")
    logger.info("=" * 60)
    
    # Fix admin commands
    fix_admin_commands()
    
    # Fix worker count
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
