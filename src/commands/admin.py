from telegram import Update, constants
from telegram.ext import ContextTypes
from src.decorators import admin_only
from datetime import datetime

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message_to_send = ' '.join(context.args)
    db = context.bot_data['db']
    logger = context.bot_data['logger']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    users = await db.get_all_users()
    if not users:
        await update.message.reply_text("No users to broadcast to.")
        return
    success_count, fail_count = 0, 0
    await update.message.reply_text(f"📤 Broadcasting to {len(users)} users...")
    for user in users:
        try:
            await context.bot.send_message(user['user_id'], f"📢 **Broadcast:**\n\n{message_to_send}", parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"Broadcast failed for {user['user_id']}: {e}")
    await update.message.reply_text(f"✅ Broadcast complete! Success: {success_count}, Failed: {fail_count}")

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data['db']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    stats_data = await db.get_stats()
    text = (f"📊 **Bot Statistics:**\n\n👥 Total Users: {stats_data['total_users']}\n✅ Active Subs: {stats_data['active_subscriptions']}\n"
            f"📨 Messages Today: {stats_data['messages_today']}\n💰 Revenue This Month: ${stats_data['revenue_this_month']:.2f}")
    await update.message.reply_text(text, parse_mode='Markdown')

@admin_only
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /user <user_id>")
        return
    try: user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid user ID.")
        return
    db = context.bot_data['db']
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    sub = await db.get_user_subscription(user_id)
    dests = await db.get_destinations(user_id)
    name = (user.get('first_name') or '') + (' ' + user.get('last_name') if user.get('last_name') else '')
    text = (f"👤 **User Info:**\n\n🆔 ID: `{user['user_id']}`\nUsername: @{user['username'] or 'N/A'}\n"
            f"📝 Name: {name.strip() or 'N/A'}\n📅 Joined: {datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d')}\n\n"
            f"**Subscription:**")
    if sub and sub['is_active']:
        expires = datetime.fromisoformat(sub['expires'])
        text += f"\n✅ Active: **{sub['tier'].title()}**\n📅 Expires: {expires.strftime('%Y-%m-%d')}"
    else:
        text += "\n❌ No active subscription"
    text += f"\n\n🎯 Destinations: {len(dests)}"
    await update.message.reply_text(text, parse_mode='Markdown')
