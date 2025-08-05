import logging
import traceback
import asyncio
from datetime import datetime
from typing import Callable, Any
from functools import wraps
from telegram import Update, constants
from telegram.ext import ContextTypes

class ErrorHandler:
    """Comprehensive error handling system for production use."""
    
    def __init__(self, logger: logging.Logger, admin_id: int = None):
        self.logger = logger
        self.admin_id = admin_id
        self.error_counts = {}
        self.max_errors_per_hour = 10
        
    def handle_errors(self, func: Callable) -> Callable:
        """Decorator to handle errors gracefully."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await self._log_and_handle_error(e, func.__name__, args, kwargs)
                # Return graceful error response
                return await self._get_error_response(e, args)
        return wrapper
    
    async def _log_and_handle_error(self, error: Exception, func_name: str, args: tuple, kwargs: dict):
        """Log error and handle it appropriately."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Create detailed error log
        error_details = {
            'function': func_name,
            'error_type': error_type,
            'error_message': error_msg,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }
        
        # Log error
        self.logger.error(f"Error in {func_name}: {error_type}: {error_msg}")
        self.logger.debug(f"Full traceback: {error_details['traceback']}")
        
        # Track error frequency
        self._track_error(error_type)
        
        # Notify admin if critical
        if self._is_critical_error(error_type):
            await self._notify_admin(error_details)
    
    def _track_error(self, error_type: str):
        """Track error frequency to prevent spam."""
        now = datetime.now()
        if error_type not in self.error_counts:
            self.error_counts[error_type] = []
        
        # Remove old errors (older than 1 hour)
        self.error_counts[error_type] = [
            time for time in self.error_counts[error_type] 
            if (now - time).total_seconds() < 3600
        ]
        
        self.error_counts[error_type].append(now)
    
    def _is_critical_error(self, error_type: str) -> bool:
        """Determine if error is critical enough to notify admin."""
        critical_errors = [
            'DatabaseError', 'ConnectionError', 'TimeoutError',
            'PaymentError', 'WorkerError', 'TelegramError'
        ]
        return error_type in critical_errors or len(self.error_counts.get(error_type, [])) > self.max_errors_per_hour
    
    async def _notify_admin(self, error_details: dict):
        """Notify admin about critical errors."""
        if not self.admin_id:
            return
            
        try:
            message = (
                f"🚨 **Critical Error Detected**\n\n"
                f"**Function:** `{error_details['function']}`\n"
                f"**Error:** `{error_details['error_type']}`\n"
                f"**Message:** {error_details['error_message']}\n"
                f"**Time:** {error_details['timestamp']}"
            )
            
            # Send to admin (you'll need to implement this with your bot instance)
            # await bot.send_message(self.admin_id, message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Failed to notify admin: {e}")
    
    async def _get_error_response(self, error: Exception, args: tuple) -> str:
        """Get user-friendly error response."""
        error_type = type(error).__name__
        
        # User-friendly error messages
        error_messages = {
            'DatabaseError': "Database connection issue. Please try again in a moment.",
            'ConnectionError': "Network connection problem. Please check your internet and try again.",
            'TimeoutError': "Request timed out. Please try again.",
            'PaymentError': "Payment processing issue. Please try again or contact support.",
            'WorkerError': "Service temporarily unavailable. Please try again in a few minutes.",
            'TelegramError': "Telegram service issue. Please try again.",
        }
        
        return error_messages.get(error_type, "An unexpected error occurred. Please try again.")
    
    def get_error_stats(self) -> dict:
        """Get error statistics for monitoring."""
        stats = {}
        for error_type, times in self.error_counts.items():
            stats[error_type] = len(times)
        return stats

# Global error handler instance
error_handler = None

def initialize_error_handler(logger: logging.Logger, admin_id: int = None):
    """Initialize the global error handler."""
    global error_handler
    error_handler = ErrorHandler(logger, admin_id)
    return error_handler

def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in any function."""
    if error_handler is None:
        # Fallback if not initialized
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Unhandled error in {func.__name__}: {e}")
                return "An error occurred. Please try again."
        return wrapper
    
    return error_handler.handle_errors(func) 