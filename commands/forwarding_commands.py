from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging

logger = logging.getLogger(__name__)

async def add_destination_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds the chat where the command is called as a destination."""
    chat = update.effective_chat
    user_id = update.effective_user.id
    db = context.bot_data['db']

    # Block users from adding the bot's private chat as a destination
    if chat.type == 'private':
        await update.message.reply_text(
            "You can only run this command inside a group or channel you want to add as a destination."
        )
        return

    # Check for subscription
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await update.message.reply_text("You need an active subscription to add destinations.")
        return

    chat_id = chat.id
    chat_title = chat.title
    chat_type = chat.type

    success = await db.add_destination(user_id, chat_type, str(chat_id), chat_title)

    if success:
        await update.message.reply_text(f"✅ Success! This {chat_type}, '{chat_title}', has been added as a forwarding destination.")
    else:
        await update.message.reply_text("❌ An error occurred. It might already be in your destination list.")

async def list_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show per-slot destination manager for the current user."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    try:
        slots = await db.get_user_slots(user_id)
        if not slots:
            await update.message.reply_text(
                "📋 Your Ad Slots\n\nNo slots found. Use /my_ads to create slots first."
            )
            return
        lines = ["📋 Select a slot to manage destinations:\n"]
        keyboard = []
        for slot in slots:
            slot_id = slot['id']
            slot_num = slot['slot_number']
            keyboard.append([InlineKeyboardButton(f"Manage Slot {slot_num}", callback_data=f"dest:slot:{slot_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="cmd:my_ads")])
        await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error listing user slots for destinations: {e}")
        await update.message.reply_text("❌ Error loading slots.")

async def _render_slot_destinations(query, db, slot_id: int):
    dests = await db.get_destinations_for_slot(slot_id)
    lines = [f"🎯 Slot Destinations (slot {slot_id}):\n"]
    keyboard = []
    if dests:
        for d in dests[:80]:
            did = d.get('destination_id')
            name = d.get('destination_name') or did
            lines.append(f"• {name} ({did})")
            keyboard.append([InlineKeyboardButton(f"🗑️ Remove {name[:18]}", callback_data=f"dest:rm:{slot_id}:{did}")])
    else:
        lines.append("(none)")
    keyboard.append([InlineKeyboardButton("➕ Add from Category", callback_data=f"dest:add_menu:{slot_id}")])
    keyboard.append([InlineKeyboardButton("🧹 Clear All", callback_data=f"dest:clear:{slot_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Slot", callback_data=f"slot:{slot_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Back to My Ads", callback_data="cmd:my_ads")])
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_destinations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline destination management callbacks starting with dest:."""
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split(":")
    db = context.bot_data['db']
    if parts[1] == 'slot' and len(parts) >= 3:
        slot_id = int(parts[2])
        await _render_slot_destinations(query, db, slot_id)
        return
    if parts[1] == 'rm' and len(parts) >= 4:
        slot_id = int(parts[2])
        dest_id = parts[3]
        ok = await db.remove_slot_destination(slot_id, dest_id)
        if not ok:
            # Try legacy path by user removal
            await db.remove_destination(update.effective_user.id, dest_id)
        await _render_slot_destinations(query, db, slot_id)
        return
    if parts[1] == 'clear' and len(parts) >= 3:
        slot_id = int(parts[2])
        # Clear by replacing with empty list
        await db.update_destinations_for_slot(slot_id, [])
        await _render_slot_destinations(query, db, slot_id)
        return
    if parts[1] == 'add_menu' and len(parts) >= 3:
        slot_id = int(parts[2])
        cats = await db.get_managed_group_categories()
        rows = []
        for c in cats[:80]:
            rows.append([InlineKeyboardButton(c, callback_data=f"dest:add_cat:{slot_id}:{c}")])
        rows.append([InlineKeyboardButton("🔙 Back to Destinations", callback_data=f"dest:slot:{slot_id}")])
        await query.edit_message_text("Select a category to add all chats:", reply_markup=InlineKeyboardMarkup(rows))
        return
    if parts[1] == 'add_cat' and len(parts) >= 4:
        slot_id = int(parts[2])
        category = parts[3]
        # Merge current + category chats
        current = await db.get_destinations_for_slot(slot_id)
        current_ids = {d.get('destination_id') for d in (current or [])}
        groups = await db.get_managed_groups(category)
        # Build a de-duplicated merged list
        merged_map = {d.get('destination_id'): d for d in (current or [])}
        added = 0
        for g in groups:
            gid = g.get('group_id') or g.get('group_name')
            if gid and gid not in merged_map:
                merged_map[gid] = {
                    'destination_type': 'chat',
                    'destination_id': gid,
                    'destination_name': g.get('group_name'),
                    'alias': None,
                }
                added += 1
        merged = list(merged_map.values())
        await db.update_destinations_for_slot(slot_id, merged)
        await query.answer(f"Added {added} chats from {category}")
        await _render_slot_destinations(query, db, slot_id)
        return

async def remove_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a destination by its ID."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    try:
        # Parse destination ID from command
        command_parts = update.message.text.split()
        if len(command_parts) < 2:
            await update.message.reply_text(
                "❌ **Usage:** /remove_destination <destination_id>\n\n"
                "Use /list_destinations to see your destinations and their IDs.",
                parse_mode='Markdown'
            )
            return
        
        dest_id = command_parts[1]
        
        # Remove destination
        success = await db.remove_destination(user_id, dest_id)
        
        if success:
            await update.message.reply_text(
                f"✅ **Destination Removed**\n\n"
                f"Destination ID `{dest_id}` has been removed from your list.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **Error**\n\n"
                "Could not remove destination. It might not exist or you don't have permission.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error removing destination: {e}")
        await update.message.reply_text("❌ Error removing destination. Please try again.")

async def handle_remove_destination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove destination callback."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse destination ID from callback data
        dest_id = query.data.split(":")[1]
        user_id = update.effective_user.id
        db = context.bot_data['db']
        
        # Remove destination
        success = await db.remove_destination(user_id, dest_id)
        
        if success:
            await query.edit_message_text(
                f"✅ **Destination Removed**\n\n"
                f"Destination has been removed from your list.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ **Error**\n\n"
                "Could not remove destination. Please try again.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error handling remove destination callback: {e}")
        await query.edit_message_text(
            "❌ Error removing destination. Please try again.",
            parse_mode='Markdown'
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """A general cancel command for conversations."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END