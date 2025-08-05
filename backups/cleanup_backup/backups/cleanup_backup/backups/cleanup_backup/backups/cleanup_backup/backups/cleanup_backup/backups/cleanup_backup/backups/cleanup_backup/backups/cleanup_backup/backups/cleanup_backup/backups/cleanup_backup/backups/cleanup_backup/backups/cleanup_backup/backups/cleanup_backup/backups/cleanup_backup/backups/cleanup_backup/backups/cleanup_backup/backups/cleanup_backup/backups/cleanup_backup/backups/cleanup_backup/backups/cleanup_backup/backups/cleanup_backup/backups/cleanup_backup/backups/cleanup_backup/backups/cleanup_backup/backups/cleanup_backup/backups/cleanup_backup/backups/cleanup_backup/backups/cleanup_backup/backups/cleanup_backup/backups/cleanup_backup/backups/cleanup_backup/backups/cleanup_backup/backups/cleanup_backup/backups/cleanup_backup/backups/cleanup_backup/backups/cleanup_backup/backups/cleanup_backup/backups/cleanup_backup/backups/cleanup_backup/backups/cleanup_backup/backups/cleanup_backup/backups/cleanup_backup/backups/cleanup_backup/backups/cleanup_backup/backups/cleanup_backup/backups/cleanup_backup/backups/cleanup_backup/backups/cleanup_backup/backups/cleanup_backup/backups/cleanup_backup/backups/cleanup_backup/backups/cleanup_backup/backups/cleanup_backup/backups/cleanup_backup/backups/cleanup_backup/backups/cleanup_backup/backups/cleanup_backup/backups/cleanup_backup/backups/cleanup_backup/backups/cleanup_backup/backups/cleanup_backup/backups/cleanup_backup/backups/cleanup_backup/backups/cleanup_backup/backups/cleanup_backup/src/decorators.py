from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import time

def admin_only(func):
    """Decorator to restrict command to admin only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        config = context.bot_data.get('config')
        if not config or not hasattr(config, 'is_admin'):
            return
            
        if not config.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ This command is for administrators only.")
            return
            
        return await func(update, context)
    return wrapper

def rate_limit(limit: int = 5, window: int = 60):
    """
    Decorator to rate limit command usage.
    :param limit: Max number of calls.
    :param window: Time window in seconds.
    """
    def decorator(func):
        user_calls = {}

        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            now = time.time()

            call_history = user_calls.get(user_id, [])
            valid_calls = [t for t in call_history if now - t < window]
            user_calls[user_id] = valid_calls

            if len(valid_calls) >= limit:
                time_left = int(window - (now - valid_calls[0]))
                await update.message.reply_text(
                    f"⏳ Rate limit exceeded. Please wait {time_left} seconds before trying again."
                )
                return

            user_calls[user_id].append(now)
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator