from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
#!/usr/bin/env python3
"""
Payment Commands

This module handles payment-related commands.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

from src.payment.direct_payment import get_direct_payment_processor

logger = logging.getLogger(__name__)

async def cmd_crypto_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cryptocurrency selection for payments."""
    try:
        # Get user data
        user_id = update.effective_user.id
        
        # Get selected tier
        if not context.user_data.get('selected_tier'):
            await update.callback_query.answer("Please select a subscription tier first")
            return
        
        tier = context.user_data.get('selected_tier')
        
        # Get direct payment processor
        payment_processor = get_direct_payment_processor()
        if not payment_processor:
            await update.callback_query.answer("Payment system not available")
            return
        
        # Get supported cryptocurrencies
        supported_cryptos = await payment_processor.get_supported_cryptos()
        
        # Create keyboard with supported cryptocurrencies
        keyboard = []
        for crypto in supported_cryptos:
            keyboard.append([InlineKeyboardButton(
                f"Pay with {crypto}", 
                callback_data=f"pay_{crypto.lower()}_{tier}"
            )])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("Back", callback_data="subscription_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message
        await update.callback_query.edit_message_text(
            f"Select cryptocurrency for {tier.capitalize()} subscription:",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing crypto selection: {e}")
        await update.callback_query.answer("An error occurred")

async def cmd_create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a payment for the selected cryptocurrency."""
    try:
        # Get callback data
        callback_data = update.callback_query.data
        
        # Parse callback data
        parts = callback_data.split('_')
        if len(parts) < 3:
            await update.callback_query.answer("Invalid selection")
            return
        
        crypto_type = parts[1].upper()
        tier = parts[2]
        
        # Get user data
        user_id = update.effective_user.id
        
        # Get direct payment processor
        payment_processor = get_direct_payment_processor()
        if not payment_processor:
            await update.callback_query.answer("Payment system not available")
            return
        
        # Create payment
        payment_raw = await payment_processor.create_payment(user_id, crypto_type, tier)
        payment = fix_payment_data(payment_raw)
        
        if 'error' in payment:
            await update.callback_query.answer(f"Error: {payment['error']}")
            return
        
        # Format amount
        amount_crypto = payment['amount_crypto']
        
        # Create message
        message = f"💰 *{tier.capitalize()} Subscription Payment*\n\n"
        message += f"• Amount: *{amount_crypto} {crypto_type}*\n"
        message += f"• Address: `{payment['address']}`\n"
        message += f"• Payment ID: `{payment['payment_id']}`\n\n"
        message += "Please send the exact amount to the address above.\n"
        message += "Your subscription will be activated automatically once payment is confirmed.\n\n"
        message += "Payment expires in 60 minutes."
        
        # Create keyboard
        keyboard = [
            [InlineKeyboardButton("Check Payment Status", callback_data=f"check_{payment['payment_id']}")],
            [InlineKeyboardButton("Back to Menu", callback_data="subscription_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        await update.callback_query.answer("An error occurred")

async def cmd_check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check payment status."""
    try:
        # Get callback data
        callback_data = update.callback_query.data
        
        # Parse callback data
        parts = callback_data.split('_')
        if len(parts) < 2:
            await update.callback_query.answer("Invalid selection")
            return
        
        payment_id = parts[1]
        
        # Get user data
        user_id = update.effective_user.id
        
        # Get direct payment processor
        payment_processor = get_direct_payment_processor()
        if not payment_processor:
            await update.callback_query.answer("Payment system not available")
            return
        
        # For now, just show a message
        await update.callback_query.answer("Payment verification in progress...")
        
        # Create keyboard
        keyboard = [
            [InlineKeyboardButton("Refresh Status", callback_data=f"check_{payment_id}")],
            [InlineKeyboardButton("Back to Menu", callback_data="subscription_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message
        await update.callback_query.edit_message_text(
            "Payment verification in progress. This may take a few minutes.\n\n"
            "Your subscription will be activated automatically once payment is confirmed.",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        await update.callback_query.answer("An error occurred")
