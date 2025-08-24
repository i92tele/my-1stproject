#!/usr/bin/env python3
"""
Quick Worker Status Fix

This script provides a simple replacement for the worker status function
to prevent the bot from freezing.
"""

def get_fixed_worker_status_function():
    """Get the fixed worker status function code."""
    return '''async def worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show worker status and usage."""
    if not await check_admin(update, context):
        await send_admin_message(update, "❌ Admin access required.")
        return
    
    try:
        db = context.bot_data.get('db')
        if not db:
            await send_admin_message(update, "❌ Database not available.")
            return
        
        workers = await db.get_all_workers()
        if not workers:
            await send_admin_message(update, "🤖 No workers found.")
            return
        
        # Simple summary to avoid freezing
        lines = ["🤖 **Worker Status Summary**\\n"]
        lines.append(f"📊 **Overview:**")
        lines.append(f"• Total Workers: {len(workers)}")
        
        # Get basic stats without detailed processing
        available_count = 0
        total_hourly = 0
        total_daily = 0
        
        # Process only first 20 workers to avoid timeout
        for i, worker in enumerate(workers[:20]):
            try:
                usage = await db.get_worker_usage(worker['worker_id']) or {}
                if usage.get('is_available', True):
                    available_count += 1
                total_hourly += usage.get('hourly_posts', 0)
                total_daily += usage.get('daily_posts', 0)
            except Exception as e:
                logger.warning(f"Error getting usage for worker {worker['worker_id']}: {e}")
                continue
        
        lines.append(f"• Available: {available_count}")
        lines.append(f"• Total Hourly Posts: {total_hourly}")
        lines.append(f"• Total Daily Posts: {total_daily}")
        
        if len(workers) > 20:
            lines.append(f"• Note: Showing stats for first 20 of {len(workers)} workers")
        
        # Add workload information
        try:
            due_slots = await db.get_active_ads_to_send()
            user_slots = [slot for slot in due_slots if slot.get('slot_type') == 'user']
            admin_slots = [slot for slot in due_slots if slot.get('slot_type') == 'admin']
            
            lines.append("")
            lines.append(f"📋 **Current Workload:**")
            lines.append(f"• User ads pending: {len(user_slots)}")
            lines.append(f"• Admin ads pending: {len(admin_slots)}")
            lines.append(f"• Total workload: {len(due_slots)}")
        except Exception as e:
            logger.warning(f"Error getting workload info: {e}")
            lines.append("")
            lines.append(f"📋 **Current Workload:** Unable to load")
        
        await send_admin_message(update, "\\n".join(lines), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        await send_admin_message(update, "❌ Error getting worker status.")'''

def main():
    """Main function."""
    print("=" * 60)
    print("🔧 QUICK WORKER STATUS FIX")
    print("=" * 60)
    
    print("📋 MANUAL FIX INSTRUCTIONS:")
    print("")
    print("1. Open commands/admin_commands.py")
    print("2. Find the worker_status function (around line 1806)")
    print("3. Replace the entire function with the code below:")
    print("")
    print("-" * 60)
    print(get_fixed_worker_status_function())
    print("-" * 60)
    print("")
    print("4. Save the file")
    print("5. Restart the bot")
    print("6. Test the worker status button")
    print("")
    print("✅ This should fix the freezing issue!")
    print("=" * 60)

if __name__ == "__main__":
    main()
