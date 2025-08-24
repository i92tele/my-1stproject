from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, constants
from telegram.ext import ContextTypes
from src.decorators import rate_limit

@rate_limit()
async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = context.bot_data['db']
    message = update.callback_query.message if update.callback_query else update.message
    if update.callback_query: await update.callback_query.answer()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await message.reply_text("❌ You need an active subscription to add destinations.")
        return
    tier_info = context.bot_data['config'].subscription_tiers.get(subscription['tier'], {})
    current_destinations = await db.get_destinations(user_id)
    max_dest = tier_info.get('max_destinations', 0)
    if max_dest != -1 and len(current_destinations) >= max_dest:
        await message.reply_text(f"❌ You've reached the max of {max_dest} destinations for your plan.")
        return
    context.user_data['adding_destination'] = True
    await message.reply_text("Forward a message from the destination channel/group, or /cancel.", reply_markup=ForceReply(selective=True))

@rate_limit()
async def list_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = context.bot_data['db']
    message = update.callback_query.message if update.callback_query else update.message
    if update.callback_query: await update.callback_query.answer()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    destinations = await db.get_destinations(user_id)
    if not destinations:
        keyboard = [[InlineKeyboardButton("➕ Add First Destination", callback_data="add_destination_shortcut")]]
        await message.reply_text("📭 You have no forwarding destinations.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    text = "📋 **Your Forwarding Destinations:**\n\n"
    keyboard = []
    for dest in destinations:
        display_name = dest['alias'] or dest['destination_name']
        emoji = "📢" if dest['destination_type'] == 'channel' else "👥"
        text += f"• {emoji} **{display_name}** (ID: `{dest['id']}`)\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ Remove '{display_name}'", callback_data=f"remove_dest_{dest['id']}")])
    text += "\nUse `/set_alias` to rename."
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def remove_destination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dest_id = int(query.data.split('_')[-1])
    user_id = query.from_user.id
    db = context.bot_data['db']
    destination = await db.get_destination_by_id(dest_id, user_id)
    if destination and await db.remove_destination(user_id, dest_id):
        await query.edit_message_text(f"✅ Destination '{destination['alias']}' removed.")
        await list_destinations(update, context)
    else:
        await query.edit_message_text("❌ Error: Failed to remove destination.")
