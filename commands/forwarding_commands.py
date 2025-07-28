from telegram import Update, ForceReply, Message
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new forwarding destination."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    # Check subscription
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        await update.message.reply_text(
            "? You need an active subscription to add destinations.\n"
            "Use /subscribe to get started!"
        )
        return
    
    # Check destination limit
    config = context.bot_data['config']
    tier_info = config.get_tier_info(subscription['tier'])
    current_destinations = await db.get_destinations(user_id)
    
    max_destinations = tier_info['max_destinations']
    if max_destinations > 0 and len(current_destinations) >= max_destinations:
        await update.message.reply_text(
            f"? You've reached the maximum number of destinations ({max_destinations}) "
            f"for your {subscription['tier']} plan.\n\n"
            "Upgrade your plan or remove existing destinations."
        )
        return
    
    # Start conversation
    context.user_data['adding_destination'] = True
    
    await update.message.reply_text(
        "?? **Adding New Destination**\n\n"
        "Please forward a message from the channel/group you want to add as a destination.\n\n"
        "**Requirements:**\n"
        "• You must be an admin in that channel/group\n"
        "• The bot must be added to that channel/group\n\n"
        "Or use /cancel to cancel this operation.",
        reply_markup=ForceReply(selective=True),
        parse_mode='Markdown'
    )

async def list_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's forwarding destinations."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    ui = context.bot_data['ui']
    
    destinations = await db.get_destinations(user_id)
    
    if not destinations:
        await update.message.reply_text(
            "?? You don't have any forwarding destinations yet.\n"
            "Use /add_destination to add one!"
        )
        return
    
    # Use UI to create destinations keyboard
    keyboard = ui.get_destinations_keyboard(destinations)
    
    text = "?? **Your Forwarding Destinations:**\n\n"
    
    for i, dest in enumerate(destinations, 1):
        emoji = "??" if dest['destination_type'] == 'channel' else "??"
        status = "?" if dest['is_active'] else "?"
        text += f"{i}. {emoji} **{dest['destination_name']}** {status}\n"
        text += f"   ID: `{dest['id']}`\n\n"
    
    text += "Click on a destination to manage it, or use:\n"
    text += "`/remove_destination <ID>` to remove"
    
    await update.message.reply_text(
        text, 
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def remove_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a forwarding destination."""
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /remove_destination <destination_id>\n\n"
            "Use /list_destinations to see IDs"
        )
        return
    
    try:
        dest_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid destination ID")
        return
    
    # Remove the destination
    success = await db.remove_destination(user_id, dest_id)
    
    if success:
        await update.message.reply_text("? Destination removed successfully!")
    else:
        await update.message.reply_text(
            "? Failed to remove destination. "
            "Make sure the ID is correct and belongs to you."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages for forwarding."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    
    # Check if user is adding a destination
    if context.user_data.get('adding_destination'):
        await _handle_destination_add(update, context)
        return
    
    # Check user subscription
    db = context.bot_data['db']
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['is_active']:
        return
    
    # Get user's destinations
    destinations = await db.get_destinations(user_id)
    if not destinations:
        await update.message.reply_text(
            "?? Tip: Add a destination first using /add_destination"
        )
        return
    
    # Forward to all destinations
    await _forward_to_destinations(update.message, destinations, context)
    
    # Update statistics
    await db.increment_message_count(user_id)
    
    # Send confirmation
    await update.message.reply_text(
        f"? Message forwarded to {len(destinations)} destination(s)!"
    )

async def _handle_destination_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a new destination from forwarded message."""
    message = update.message
    user_id = update.effective_user.id
    db = context.bot_data['db']
    
    # Check if this is a forwarded message from a channel/group
    if not message.forward_from_chat:
        await message.reply_text(
            "? Please forward a message from a channel or group.\n"
            "Make sure you're an admin in that chat."
        )
        return
    
    chat = message.forward_from_chat
    
    # Verify bot has access to the chat
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        if bot_member.status not in ['administrator', 'member']:
            raise Exception("Bot not in chat")
    except:
        await message.reply_text(
            "? I need to be added to that chat first!\n"
            "Please add me as an admin to the channel/group and try again."
        )
        context.user_data.pop('adding_destination', None)
        return
    
    # Verify user is admin in the chat (for groups/channels)
    if chat.type in ['group', 'supergroup', 'channel']:
        try:
            user_member = await context.bot.get_chat_member(chat.id, user_id)
            if user_member.status not in ['creator', 'administrator']:
                await message.reply_text(
                    "? You need to be an admin in that chat to add it as a destination."
                )
                context.user_data.pop('adding_destination', None)
                return
        except:
            await message.reply_text("? Couldn't verify your admin status in that chat.")
            context.user_data.pop('adding_destination', None)
            return
    
    # Add the destination
    dest_type = 'channel' if chat.type == 'channel' else 'group'
    success = await db.add_destination(
        user_id=user_id,
        dest_type=dest_type,
        dest_id=str(chat.id),
        dest_name=chat.title
    )
    
    if success:
        await message.reply_text(
            f"? Successfully added **{chat.title}** as a forwarding destination!\n\n"
            "Messages you send to this bot will now be forwarded there.",
            parse_mode='Markdown'
        )
    else:
        await message.reply_text("? Failed to add destination. Please try again.")
    
    context.user_data.pop('adding_destination', None)

async def _forward_to_destinations(message: Message, destinations: list, 
                                 context: ContextTypes.DEFAULT_TYPE):
    """Forward message to all destinations."""
    logger = context.bot_data['logger']
    
    for dest in destinations:
        try:
            chat_id = int(dest['destination_id'])
            
            # Forward based on message type
            if message.text:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message.text,
                    entities=message.entities,
                    disable_web_page_preview=True
                )
            elif message.photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=chat_id,
                    voice=message.voice.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.sticker:
                await context.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                await context.bot.send_animation(
                    chat_id=chat_id,
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
                
        except Exception as e:
            logger.error(f"Failed to forward to {dest['destination_name']}: {e}")

async def handle_destination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination management callbacks."""
    query = update.callback_query
    data = query.data
    
    if data == "add_destination":
        # Switch to message handler for adding destination
        context.user_data['adding_destination'] = True
        await query.message.reply_text(
            "Please forward a message from the channel/group you want to add.",
            reply_markup=ForceReply(selective=True)
        )
        await query.answer()
    
    elif data == "manage_destinations":
        await query.message.reply_text(
            "Use /list_destinations to see all destinations\n"
            "Use /remove_destination <ID> to remove a destination"
        )
        await query.answer()
    
    elif data.startswith("dest:"):
        dest_id = int(data.split(":")[1])
        await query.message.reply_text(
            f"To remove this destination, use:\n"
            f"`/remove_destination {dest_id}`",
            parse_mode='Markdown'
        )
        await query.answer()