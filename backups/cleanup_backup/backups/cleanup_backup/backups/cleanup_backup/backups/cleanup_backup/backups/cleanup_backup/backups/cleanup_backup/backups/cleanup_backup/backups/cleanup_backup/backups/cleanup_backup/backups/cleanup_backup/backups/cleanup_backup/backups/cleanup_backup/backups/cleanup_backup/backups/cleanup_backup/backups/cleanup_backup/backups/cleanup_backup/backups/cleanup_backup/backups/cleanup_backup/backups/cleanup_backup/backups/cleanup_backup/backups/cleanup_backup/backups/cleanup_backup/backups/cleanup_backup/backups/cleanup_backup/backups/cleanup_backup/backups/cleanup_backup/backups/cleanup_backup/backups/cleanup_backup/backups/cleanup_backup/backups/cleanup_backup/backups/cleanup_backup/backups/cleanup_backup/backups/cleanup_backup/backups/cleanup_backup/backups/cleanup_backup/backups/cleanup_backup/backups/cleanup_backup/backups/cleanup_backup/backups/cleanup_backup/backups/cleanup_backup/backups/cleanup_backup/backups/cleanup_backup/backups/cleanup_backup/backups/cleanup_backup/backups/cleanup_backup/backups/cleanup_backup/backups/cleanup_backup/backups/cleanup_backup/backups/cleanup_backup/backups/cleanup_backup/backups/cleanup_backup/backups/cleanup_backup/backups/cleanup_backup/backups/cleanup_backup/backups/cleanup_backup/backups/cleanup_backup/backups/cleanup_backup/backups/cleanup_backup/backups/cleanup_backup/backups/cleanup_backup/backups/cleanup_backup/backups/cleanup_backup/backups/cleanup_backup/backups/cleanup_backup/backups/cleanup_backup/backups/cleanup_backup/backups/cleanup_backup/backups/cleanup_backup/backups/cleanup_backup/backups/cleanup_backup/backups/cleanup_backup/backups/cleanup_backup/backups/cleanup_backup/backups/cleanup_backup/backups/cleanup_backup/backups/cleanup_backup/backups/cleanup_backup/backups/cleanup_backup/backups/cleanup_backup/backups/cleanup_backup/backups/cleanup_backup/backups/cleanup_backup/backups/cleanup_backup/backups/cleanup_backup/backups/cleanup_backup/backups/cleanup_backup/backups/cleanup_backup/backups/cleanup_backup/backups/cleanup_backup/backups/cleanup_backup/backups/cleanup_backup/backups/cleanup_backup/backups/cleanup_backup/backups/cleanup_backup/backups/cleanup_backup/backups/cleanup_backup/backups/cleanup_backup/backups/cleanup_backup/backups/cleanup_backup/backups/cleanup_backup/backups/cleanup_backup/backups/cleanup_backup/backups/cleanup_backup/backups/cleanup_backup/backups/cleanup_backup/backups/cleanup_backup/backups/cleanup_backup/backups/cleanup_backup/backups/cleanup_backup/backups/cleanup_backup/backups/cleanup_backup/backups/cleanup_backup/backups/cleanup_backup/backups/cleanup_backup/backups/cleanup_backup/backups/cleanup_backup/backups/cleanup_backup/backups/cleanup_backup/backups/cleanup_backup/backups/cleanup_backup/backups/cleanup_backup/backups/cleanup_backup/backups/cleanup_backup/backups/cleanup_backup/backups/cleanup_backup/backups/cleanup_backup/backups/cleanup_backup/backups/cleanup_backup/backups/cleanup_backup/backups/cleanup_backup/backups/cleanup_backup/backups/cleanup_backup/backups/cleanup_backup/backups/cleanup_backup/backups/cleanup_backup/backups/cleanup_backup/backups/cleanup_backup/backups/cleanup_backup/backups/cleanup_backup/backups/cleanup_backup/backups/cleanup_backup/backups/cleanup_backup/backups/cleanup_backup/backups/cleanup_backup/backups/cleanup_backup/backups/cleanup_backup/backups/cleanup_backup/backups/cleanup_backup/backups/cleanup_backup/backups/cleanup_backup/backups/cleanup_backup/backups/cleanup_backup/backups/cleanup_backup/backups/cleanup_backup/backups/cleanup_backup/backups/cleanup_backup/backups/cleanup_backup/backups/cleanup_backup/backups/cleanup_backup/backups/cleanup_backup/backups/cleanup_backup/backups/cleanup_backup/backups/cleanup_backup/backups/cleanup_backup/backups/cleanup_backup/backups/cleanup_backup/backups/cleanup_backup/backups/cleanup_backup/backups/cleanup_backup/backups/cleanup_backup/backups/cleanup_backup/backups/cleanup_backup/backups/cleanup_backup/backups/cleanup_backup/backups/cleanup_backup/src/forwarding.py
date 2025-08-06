from typing import List, Dict, Any
from telegram import Update, Message, constants
from telegram.ext import ContextTypes

class MessageForwarder:
    """Handle message forwarding logic."""

    def __init__(self, db, config, logger, message_filter):
        self.db = db
        self.config = config
        self.logger = logger
        self.message_filter = message_filter

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process incoming messages for forwarding."""
        if not update.message:
            return

        user_id = update.effective_user.id

        if context.user_data.get('adding_destination'):
            await self._handle_destination_add(update, context)
            return

        subscription = await self.db.get_user_subscription(user_id)
        if not subscription or not subscription['is_active']:
            return

        destinations = await self.db.get_destinations(user_id)
        if not destinations:
            return

        if not await self.message_filter.should_forward(update.message, user_id):
            return

        await self._forward_to_destinations(update.message, destinations, context)
        await self.db.increment_message_count(user_id)

    async def handle_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edited messages for forwarding."""
        if not update.edited_message:
            return
        message = update.edited_message
        user_id = update.effective_user.id
        subscription = await self.db.get_user_subscription(user_id)
        if not subscription or not subscription['is_active']:
            return
        destinations = await self.db.get_destinations(user_id)
        if not destinations:
            return
        if message.text:
            message.text = f"✍️ (edited): {message.text}"
        elif message.caption:
            message.caption = f"✍️ (edited): {message.caption}"
        await self._forward_to_destinations(message, destinations, context)

    async def _handle_destination_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding a new destination from forwarded message."""
        message = update.message
        user_id = update.effective_user.id

        if not message.forward_from_chat:
            await message.reply_text("❌ Please forward a message from a channel or group, or /cancel.")
            return

        chat = message.forward_from_chat
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

        try:
            bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if bot_member.status not in ['administrator', 'member']:
                raise Exception("Bot not in chat or not an admin.")
        except Exception:
            await message.reply_text("❌ I need to be in that chat first! Please add me and try again.")
            context.user_data.pop('adding_destination', None)
            return

        dest_type = 'channel' if chat.type == 'channel' else 'group'
        success = await self.db.add_destination(
            user_id=user_id,
            dest_type=dest_type,
            dest_id=str(chat.id),
            dest_name=chat.title
        )

        if success:
            await message.reply_text(f"✅ Successfully added '{chat.title}' as a forwarding destination!")
        else:
            await message.reply_text("❌ Failed to add destination. It might already be in your list.")

        context.user_data.pop('adding_destination', None)

    async def _forward_to_destinations(self, message: Message, destinations: List[Dict[str, Any]], context: ContextTypes.DEFAULT_TYPE):
        """Forward message to all destinations."""
        for dest in destinations:
            try:
                chat_id = int(dest['destination_id'])
                await message.copy(chat_id=chat_id)
            except Exception as e:
                self.logger.error(f"Failed to forward to {dest['destination_name']} ({chat_id}): {e}")
                try:
                    await message.reply_text(f"⚠️ Failed to forward to '{dest['alias'] or dest['destination_name']}'. "
                                             "I might have been removed or lost permissions there.")
                except Exception:
                    pass
