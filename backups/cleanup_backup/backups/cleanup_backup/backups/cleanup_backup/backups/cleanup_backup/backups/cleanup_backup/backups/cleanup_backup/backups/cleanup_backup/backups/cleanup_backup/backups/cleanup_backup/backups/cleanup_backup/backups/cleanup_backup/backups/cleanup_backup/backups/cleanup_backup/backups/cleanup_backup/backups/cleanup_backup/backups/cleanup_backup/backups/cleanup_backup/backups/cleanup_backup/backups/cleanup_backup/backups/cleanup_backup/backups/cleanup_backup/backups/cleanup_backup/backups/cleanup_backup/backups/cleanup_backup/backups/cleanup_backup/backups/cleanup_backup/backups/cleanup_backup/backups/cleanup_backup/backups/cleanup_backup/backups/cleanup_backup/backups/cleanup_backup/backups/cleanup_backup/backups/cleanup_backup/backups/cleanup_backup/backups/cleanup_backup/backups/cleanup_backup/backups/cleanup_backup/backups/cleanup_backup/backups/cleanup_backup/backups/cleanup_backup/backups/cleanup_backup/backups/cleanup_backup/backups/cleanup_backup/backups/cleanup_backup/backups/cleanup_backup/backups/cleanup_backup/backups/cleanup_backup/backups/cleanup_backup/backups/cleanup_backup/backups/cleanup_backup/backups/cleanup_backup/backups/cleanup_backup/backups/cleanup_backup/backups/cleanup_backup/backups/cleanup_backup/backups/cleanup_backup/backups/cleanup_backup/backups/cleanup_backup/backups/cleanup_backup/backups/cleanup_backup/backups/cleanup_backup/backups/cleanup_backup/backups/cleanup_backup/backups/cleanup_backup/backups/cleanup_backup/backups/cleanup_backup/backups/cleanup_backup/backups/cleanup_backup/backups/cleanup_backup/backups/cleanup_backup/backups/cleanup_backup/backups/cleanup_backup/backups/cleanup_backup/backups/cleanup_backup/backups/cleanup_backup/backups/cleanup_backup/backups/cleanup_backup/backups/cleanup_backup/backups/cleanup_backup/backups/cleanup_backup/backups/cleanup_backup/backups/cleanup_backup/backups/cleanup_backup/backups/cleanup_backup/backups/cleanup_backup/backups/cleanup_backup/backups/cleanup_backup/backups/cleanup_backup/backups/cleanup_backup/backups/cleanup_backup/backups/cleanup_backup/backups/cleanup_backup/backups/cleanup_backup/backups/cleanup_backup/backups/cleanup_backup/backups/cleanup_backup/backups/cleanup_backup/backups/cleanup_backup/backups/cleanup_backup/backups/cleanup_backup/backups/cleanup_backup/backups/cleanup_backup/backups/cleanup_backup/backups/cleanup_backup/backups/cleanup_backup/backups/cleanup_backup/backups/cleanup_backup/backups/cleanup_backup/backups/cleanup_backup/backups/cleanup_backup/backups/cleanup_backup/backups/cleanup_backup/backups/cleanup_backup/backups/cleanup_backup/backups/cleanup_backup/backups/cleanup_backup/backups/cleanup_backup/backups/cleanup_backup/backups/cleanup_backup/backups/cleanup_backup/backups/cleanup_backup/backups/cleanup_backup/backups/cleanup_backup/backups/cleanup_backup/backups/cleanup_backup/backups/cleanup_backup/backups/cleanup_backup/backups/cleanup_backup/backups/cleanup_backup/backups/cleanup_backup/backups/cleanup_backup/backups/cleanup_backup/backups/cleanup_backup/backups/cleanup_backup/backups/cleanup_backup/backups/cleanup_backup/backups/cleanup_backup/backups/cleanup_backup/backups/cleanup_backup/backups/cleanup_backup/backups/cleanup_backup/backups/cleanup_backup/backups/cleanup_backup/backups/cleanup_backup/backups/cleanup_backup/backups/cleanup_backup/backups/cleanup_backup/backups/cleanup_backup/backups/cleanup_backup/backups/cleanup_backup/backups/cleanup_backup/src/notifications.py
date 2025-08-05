import logging

class NotificationManager:
    """Handle all user notifications."""
    
    def __init__(self, bot, logger: logging.Logger):
        self.bot = bot
        self.logger = logger
    
    async def _send_message(self, user_id: int, message: str):
        """Helper function to send a message safely."""
        if not self.bot:
            self.logger.warning("NotificationManager's bot instance is not set.")
            return
        try:
            await self.bot.send_message(user_id, message)
        except Exception as e:
            self.logger.error(f"Failed to send notification to user {user_id}: {e}")

    async def notify_payment_detected(self, user_id: int, amount: float, currency: str):
        """Notify user that a payment has been seen on the network."""
        message = (
            f"💰 Payment of {amount} {currency} detected!\n\n"
            "Your subscription will be activated after the transaction is confirmed on the blockchain (usually 10-20 minutes)."
        )
        await self._send_message(user_id, message)

    async def notify_subscription_expiring(self, user_id: int, days_left: int):
        """Notify user about expiring subscription."""
        day_str = "day" if days_left == 1 else "days"
        message = f"⚠️ Your subscription will expire in {days_left} {day_str}. Use /subscribe to renew!"
        await self._send_message(user_id, message)
    
    async def notify_payment_success(self, user_id: int, tier: str):
        """Notify user about successful payment."""
        message = f"✅ Payment successful! Your {tier.title()} subscription is now active."
        await self._send_message(user_id, message)