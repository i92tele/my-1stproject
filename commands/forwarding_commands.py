from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
import logging

logger = logging.getLogger(__name__)

# Define the states for the conversation to add a destination
WAITING_FORWARD = 0

async def add_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to add a new destination."""
    await update.message.reply_text(
        "Please forward a message from the channel or group you want to add as a destination.\n\n"
        "Requirements:\n"
        "• Your WORKER account must be a member of the group.\n\n"
        "Use /cancel to stop."
    )
    return WAITING_FORWARD

async def receive_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and processes the forwarded message with extra debugging."""
    message = update.message
    db = context.bot_data['db']
    user_id = update.effective_user.id

    # --- Start Debugging ---
    logger.info("--- Received Forwarded Message ---")
    logger.info(f"Is message forwarded: {bool(message.forward_date)}")
    logger.info(f"Has forward_from_chat attribute: {bool(message.forward_from_chat)}")
    if message.forward_from_chat:
        logger.info(f"Forwarded from chat ID: {message.forward_from_chat.id}")
        logger.info(f"Forwarded from chat title: {message.forward_from_chat.title}")
        logger.info(f"Forwarded from chat type: {message.forward_from_chat.type}")
    logger.info("---------------------------------")
    # --- End Debugging ---

    if message.forward_from_chat and message.forward_from_chat.type in ('group', 'supergroup', 'channel'):
        chat = message.forward_from_chat
        chat_id = chat.id
        chat_title = chat.title
        chat_type = chat.type
        
        success = await db.add_destination(user_id, chat_type, str(chat_id), chat_title)
        
        if success:
            await update.message.reply_text(f"✅ Successfully added '{chat_title}' as a forwarding destination!")
        else:
            await update.message.reply_text("❌ An error occurred while adding the destination.")
            
        return ConversationHandler.END
    else:
        await update.message.reply_text("That doesn't seem to be a forwarded message from a channel or group. Please try again or use /cancel.")
        return WAITING_FORWARD

async def list_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all of the user's active destinations."""
    db = context.bot_data['db']
    user_id = update.effective_user.id
    destinations = await db.get_destinations(user_id)

    if not destinations:
        await update.message.reply_text("You have no active destinations. Use /add_destination to add one.")
        return

    message = "*Your Active Destinations:*\n\n"
    for i, dest in enumerate(destinations, 1):
        message += f"{i}. {dest['destination_name']} (ID: `{dest['destination_id']}`)\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def remove_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a destination by its ID."""
    # This is a placeholder for now. A full implementation would use a ConversationHandler
    # to ask the user which destination to remove.
    await update.message.reply_text("The /remove_destination feature is coming soon!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Note: The generic `handle_message` for direct forwarding is removed for now
# to focus on the scheduled "autoads" functionality.