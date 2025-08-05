from telegram import Update
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
    """Lists all of the user's active destinations."""
    # This is a placeholder for now.
    await update.message.reply_text("The /list_destinations feature is coming soon!")

async def remove_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a destination by its ID."""
    # This is a placeholder for now.
    await update.message.reply_text("The /remove_destination feature is coming soon!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """A general cancel command for conversations."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END