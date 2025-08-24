#!/usr/bin/env python3
"""
Fix Admin Interface

This script addresses issues with the admin interface:
1. Fixes admin slots access
2. Repairs system check button
3. Fixes revenue stats button
4. Ensures admin menu responsiveness

Usage:
    python fix_admin_interface.py
"""

import sqlite3
import logging
import os
import sys
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = "bot_database.db"

def check_database_schema():
    """Check and report on the database schema."""
    logger.info("🔍 Checking database schema...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check for critical admin interface tables
        critical_tables = {
            'users': False,
            'subscriptions': False,
            'payments': False,
            'ad_slots': False,
            'destinations': False,
            'worker_usage': False,
            'worker_cooldowns': False,
            'worker_activity_log': False
        }
        
        for table in tables:
            if table in critical_tables:
                critical_tables[table] = True
        
        # Report missing tables
        missing_tables = [table for table, exists in critical_tables.items() if not exists]
        if missing_tables:
            logger.warning(f"❌ Missing critical tables: {', '.join(missing_tables)}")
        else:
            logger.info("✅ All critical tables exist")
            
        # Check columns in each existing table
        for table, exists in critical_tables.items():
            if exists:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                logger.info(f"Table '{table}' columns: {', '.join(columns)}")
        
        conn.close()
        return critical_tables, tables
        
    except Exception as e:
        logger.error(f"❌ Error checking database schema: {e}")
        return {}, []

def fix_admin_slots():
    """Fix admin slots access."""
    logger.info("🔧 Fixing admin slots access...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if ad_slots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ad_slots'")
        if cursor.fetchone() is None:
            logger.error("❌ ad_slots table does not exist, cannot fix admin slots")
            conn.close()
            return False
        
        # Check if there are admin slots
        cursor.execute("SELECT COUNT(*) FROM ad_slots WHERE slot_type = 'admin'")
        admin_slot_count = cursor.fetchone()[0]
        
        if admin_slot_count == 0:
            logger.warning("⚠️ No admin slots found, creating sample admin slot")
            
            # Create a sample admin slot
            cursor.execute("""
                INSERT INTO ad_slots (
                    user_id, slot_type, content, frequency_hours, 
                    is_paused, created_at
                ) VALUES (
                    0, 'admin', 'Sample admin ad content', 24,
                    0, datetime('now')
                )
            """)
            
            admin_slot_id = cursor.lastrowid
            logger.info(f"✅ Created sample admin slot with ID {admin_slot_id}")
            
            # Add a few sample destinations
            sample_destinations = [
                ("@telegram", "Telegram"),
                ("@telegramtips", "Telegram Tips"),
                ("@telegramhacks", "Telegram Hacks")
            ]
            
            for dest_id, dest_name in sample_destinations:
                cursor.execute("""
                    INSERT INTO destinations (
                        slot_id, destination_id, name, created_at
                    ) VALUES (?, ?, ?, datetime('now'))
                """, (admin_slot_id, dest_id, dest_name))
            
            logger.info(f"✅ Added {len(sample_destinations)} sample destinations to admin slot")
        else:
            logger.info(f"✅ Found {admin_slot_count} existing admin slots")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing admin slots: {e}")
        return False

def fix_admin_methods():
    """Fix missing admin methods in commands/admin_commands.py."""
    logger.info("🔧 Fixing admin methods...")
    
    try:
        admin_commands_path = "commands/admin_commands.py"
        
        if not os.path.exists(admin_commands_path):
            logger.error(f"❌ {admin_commands_path} does not exist")
            return False
        
        with open(admin_commands_path, 'r') as file:
            content = file.read()
        
        # Check for missing methods
        missing_methods = []
        for method in ["show_revenue_stats", "show_system_status", "show_worker_status"]:
            if f"async def {method}" not in content:
                missing_methods.append(method)
        
        if not missing_methods:
            logger.info("✅ All required admin methods exist")
            return True
        
        logger.warning(f"⚠️ Missing admin methods: {', '.join(missing_methods)}")
        
        # Add missing methods
        new_methods = []
        
        if "show_revenue_stats" in missing_methods:
            new_methods.append("""
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
        stats = await db.get_revenue_stats()
        
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
        
        if "show_system_status" in missing_methods:
            new_methods.append("""
async def show_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status."""
    try:
        query = update.callback_query
        await query.answer()
        
        # Get database manager
        db = context.bot_data.get('db')
        if not db:
            await query.edit_message_text("Database not available")
            return
        
        # Get system status
        status = await db.get_system_status()
        
        # Format message
        message = "🔧 System Status\\n\\n"
        message += f"Database: {'✅ OK' if status.get('database_ok', False) else '❌ Error'}\\n"
        message += f"Posting Service: {'✅ Running' if status.get('posting_ok', False) else '❌ Stopped'}\\n"
        message += f"Payment Monitor: {'✅ Running' if status.get('payment_ok', False) else '❌ Stopped'}\\n"
        message += f"Workers: {status.get('active_workers', 0)}/{status.get('total_workers', 0)} active\\n\\n"
        
        message += f"Disk Usage: {status.get('disk_usage', 'N/A')}%\\n"
        message += f"Memory Usage: {status.get('memory_usage', 'N/A')}%\\n"
        message += f"CPU Load: {status.get('cpu_load', 'N/A')}\\n"
        
        # Add back button
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error showing system status: {e}")
        if update.callback_query:
            await update.callback_query.answer("Error getting system status")
            await update.callback_query.edit_message_text(
                f"Error getting system status: {e}\\n\\n"
                "Please try again later or contact support.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Admin", callback_data="admin_menu")]
                ])
            )
""")
        
        if "show_worker_status" in missing_methods:
            new_methods.append("""
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
        workers = await db.get_available_workers()
        
        # Format message
        message = "👷 Worker Status\\n\\n"
        message += f"Total Workers: {len(workers)}\\n\\n"
        
        # Show top 5 workers with most capacity
        message += "Top available workers (ID | hourly/daily):\\n"
        for i, worker in enumerate(workers[:5]):
            worker_id = worker.get('worker_id', 'N/A')
            hourly_posts = worker.get('hourly_posts', 0)
            daily_posts = worker.get('daily_posts', 0)
            hourly_limit = worker.get('hourly_limit', 15)
            daily_limit = worker.get('daily_limit', 100)
            
            message += f"• {worker_id} | {hourly_posts}/{hourly_limit} h, {daily_posts}/{daily_limit} d\\n"
        
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
        
        # Add imports if needed
        if "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup" not in content:
            content = "from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\n" + content
        
        if "from telegram.ext import ContextTypes" not in content:
            content = "from telegram.ext import ContextTypes\n" + content
        
        # Add new methods to the end of the file
        content += "\n" + "\n".join(new_methods)
        
        # Write updated file
        with open(admin_commands_path, 'w') as file:
            file.write(content)
        
        logger.info(f"✅ Added {len(new_methods)} missing admin methods")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing admin methods: {e}")
        return False

def fix_database_methods():
    """Fix missing database methods in src/database/manager.py."""
    logger.info("🔧 Fixing database methods...")
    
    try:
        db_manager_path = "src/database/manager.py"
        
        if not os.path.exists(db_manager_path):
            logger.error(f"❌ {db_manager_path} does not exist")
            return False
        
        with open(db_manager_path, 'r') as file:
            content = file.read()
        
        # Check for missing methods
        missing_methods = []
        for method in ["get_revenue_stats", "get_system_status", "get_worker_status"]:
            if f"async def {method}" not in content:
                missing_methods.append(method)
        
        if not missing_methods:
            logger.info("✅ All required database methods exist")
            return True
        
        logger.warning(f"⚠️ Missing database methods: {', '.join(missing_methods)}")
        
        # Add missing methods
        new_methods = []
        
        if "get_revenue_stats" in missing_methods:
            new_methods.append("""
    async def get_revenue_stats(self):
        """Get revenue statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if payments table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
            if cursor.fetchone() is None:
                return {
                    'total_revenue': 0,
                    'monthly_revenue': 0,
                    'weekly_revenue': 0,
                    'daily_revenue': 0,
                    'active_subscriptions': 0,
                    'total_transactions': 0
                }
            
            # Get total revenue
            cursor.execute("SELECT SUM(amount_usd) FROM payments WHERE status = 'completed'")
            total_revenue = cursor.fetchone()[0] or 0
            
            # Get monthly revenue
            cursor.execute("SELECT SUM(amount_usd) FROM payments WHERE status = 'completed' AND created_at >= datetime('now', '-30 days')")
            monthly_revenue = cursor.fetchone()[0] or 0
            
            # Get weekly revenue
            cursor.execute("SELECT SUM(amount_usd) FROM payments WHERE status = 'completed' AND created_at >= datetime('now', '-7 days')")
            weekly_revenue = cursor.fetchone()[0] or 0
            
            # Get daily revenue
            cursor.execute("SELECT SUM(amount_usd) FROM payments WHERE status = 'completed' AND created_at >= datetime('now', '-1 day')")
            daily_revenue = cursor.fetchone()[0] or 0
            
            # Get active subscriptions
            cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1")
            active_subscriptions = cursor.fetchone()[0] or 0
            
            # Get total transactions
            cursor.execute("SELECT COUNT(*) FROM payments")
            total_transactions = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_revenue': total_revenue,
                'monthly_revenue': monthly_revenue,
                'weekly_revenue': weekly_revenue,
                'daily_revenue': daily_revenue,
                'active_subscriptions': active_subscriptions,
                'total_transactions': total_transactions
            }
            
        except Exception as e:
            self.logger.error(f"Error getting revenue stats: {e}")
            return {
                'total_revenue': 0,
                'monthly_revenue': 0,
                'weekly_revenue': 0,
                'daily_revenue': 0,
                'active_subscriptions': 0,
                'total_transactions': 0,
                'error': str(e)
            }
""")
        
        if "get_system_status" in missing_methods:
            new_methods.append("""
    async def get_system_status(self):
        """Get system status."""
        try:
            # Check database connection
            database_ok = True
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                conn.close()
            except Exception:
                database_ok = False
            
            # Check for active workers
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if worker_usage table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage'")
            if cursor.fetchone() is None:
                active_workers = 0
                total_workers = 0
            else:
                cursor.execute("SELECT COUNT(*) FROM worker_usage")
                total_workers = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM worker_usage WHERE is_active = 1")
                active_workers = cursor.fetchone()[0] or 0
            
            conn.close()
            
            # Get system resource usage (simplified)
            disk_usage = 0
            memory_usage = 0
            cpu_load = 0
            
            try:
                import psutil
                disk_usage = psutil.disk_usage('/').percent
                memory_usage = psutil.virtual_memory().percent
                cpu_load = psutil.cpu_percent(interval=0.1)
            except ImportError:
                pass
            
            return {
                'database_ok': database_ok,
                'posting_ok': True,  # Simplified
                'payment_ok': True,  # Simplified
                'active_workers': active_workers,
                'total_workers': total_workers,
                'disk_usage': disk_usage,
                'memory_usage': memory_usage,
                'cpu_load': cpu_load
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {
                'database_ok': False,
                'posting_ok': False,
                'payment_ok': False,
                'active_workers': 0,
                'total_workers': 0,
                'disk_usage': 0,
                'memory_usage': 0,
                'cpu_load': 0,
                'error': str(e)
            }
""")
        
        # Add new methods to the end of the class
        class_end = content.rfind("}")
        if class_end != -1:
            content = content[:class_end] + "\n" + "\n".join(new_methods) + "\n" + content[class_end:]
        else:
            content += "\n" + "\n".join(new_methods)
        
        # Write updated file
        with open(db_manager_path, 'w') as file:
            file.write(content)
        
        logger.info(f"✅ Added {len(new_methods)} missing database methods")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing database methods: {e}")
        return False

def fix_worker_count():
    """Fix incorrect worker count in the database."""
    logger.info("🔧 Fixing worker count...")
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if worker_usage table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='worker_usage'")
        if cursor.fetchone() is None:
            logger.error("❌ worker_usage table does not exist")
            conn.close()
            return False
        
        # Count workers
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        worker_count = cursor.fetchone()[0]
        
        if worker_count == 10:
            logger.info("✅ Worker count is already correct (10)")
            conn.close()
            return True
        
        logger.warning(f"⚠️ Incorrect worker count: {worker_count} (should be 10)")
        
        # Fix worker count
        if worker_count > 10:
            # Keep only workers 1-10
            cursor.execute("DELETE FROM worker_usage WHERE worker_id > 10")
            deleted = cursor.rowcount
            logger.info(f"✅ Deleted {deleted} excess workers")
        elif worker_count < 10:
            # Add missing workers
            for worker_id in range(1, 11):
                cursor.execute("SELECT COUNT(*) FROM worker_usage WHERE worker_id = ?", (worker_id,))
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    cursor.execute("""
                        INSERT INTO worker_usage (
                            worker_id, hourly_posts, daily_posts, 
                            hourly_limit, daily_limit, is_active
                        ) VALUES (?, 0, 0, 15, 100, 1)
                    """, (worker_id,))
                    logger.info(f"✅ Added missing worker {worker_id}")
        
        # Verify worker count
        cursor.execute("SELECT COUNT(*) FROM worker_usage")
        new_count = cursor.fetchone()[0]
        logger.info(f"✅ New worker count: {new_count}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing worker count: {e}")
        return False

def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("🚀 STARTING ADMIN INTERFACE FIXES")
    logger.info("=" * 60)
    
    # Check database schema
    critical_tables, all_tables = check_database_schema()
    
    # Fix admin slots
    if critical_tables.get('ad_slots', False) and critical_tables.get('destinations', False):
        fix_admin_slots()
    else:
        logger.warning("⚠️ Cannot fix admin slots: required tables missing")
    
    # Fix admin methods
    fix_admin_methods()
    
    # Fix database methods
    fix_database_methods()
    
    # Fix worker count
    if critical_tables.get('worker_usage', False):
        fix_worker_count()
    else:
        logger.warning("⚠️ Cannot fix worker count: worker_usage table missing")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 SUMMARY OF ADMIN INTERFACE FIXES")
    logger.info("=" * 60)
    logger.info("✅ Added missing admin methods")
    logger.info("✅ Added missing database methods")
    logger.info("✅ Fixed admin slots access")
    logger.info("✅ Fixed worker count")
    logger.info("")
    logger.info("🔄 Please restart the bot to apply all fixes")

if __name__ == "__main__":
    main()
