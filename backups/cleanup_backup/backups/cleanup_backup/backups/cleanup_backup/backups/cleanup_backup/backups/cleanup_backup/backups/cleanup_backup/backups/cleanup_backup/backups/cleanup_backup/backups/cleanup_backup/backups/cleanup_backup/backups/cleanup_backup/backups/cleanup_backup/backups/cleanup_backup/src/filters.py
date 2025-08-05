from telegram import Message

class MessageFilter:
    """Filter messages based on various criteria."""

    def __init__(self, logger):
        self.logger = logger

    async def should_forward(self, message: Message, user_id: int) -> bool:
        """Determine if a message should be forwarded."""
        # Don't forward commands
        if message.text and message.text.startswith('/'):
            return False

        # Don't forward empty messages
        if not any([
            message.text, message.photo, message.video, 
            message.document, message.audio, message.voice,
            message.sticker, message.animation
        ]):
            return False

        # Future placeholder for user-specific filters
        return True
