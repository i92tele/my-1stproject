#!/usr/bin/env python3
"""
Subscription Management Commands
Handles subscription upgrades, prolonging, and user notifications
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

async def upgrade_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upgrade options for current subscription."""
    try:
        db = context.bot_data['db']
        user_id = update.effective_user.id
        
        # Get current subscription
        current_subscription = await db.get_user_subscription(user_id)
        
        if not current_subscription or not current_subscription.get('is_active'):
            await update.message.reply_text(
                "❌ You don't have an active subscription to upgrade.\n\n"
                "Please subscribe first using /subscribe"
            )
            return
        
        current_tier = current_subscription.get('tier', 'basic')
        expires = current_subscription.get('expires', 'Unknown')
        
        # Define upgrade paths
        upgrade_options = {
            'basic': {
                'next_tier': 'pro',
                'price_difference': 30,  # $45 - $15
                'additional_slots': 2,   # 3 - 1
                'description': 'Upgrade to Pro for 3 ad slots and enhanced features'
            },
            'pro': {
                'next_tier': 'enterprise',
                'price_difference': 30,  # $75 - $45
                'additional_slots': 2,   # 5 - 3
                'description': 'Upgrade to Enterprise for 5 ad slots and premium features'
            }
        }
        
        if current_tier not in upgrade_options:
            await update.message.reply_text(
                f"🎉 You already have the highest tier ({current_tier.title()})!\n\n"
                "You can prolong your subscription instead using /prolong_subscription"
            )
            return
        
        option = upgrade_options[current_tier]
        
        message_text = (
            f"🔄 **Subscription Upgrade**\n\n"
            f"**Current Plan:** {current_tier.title()}\n"
            f"**Expires:** {expires}\n\n"
            f"**Upgrade to:** {option['next_tier'].title()}\n"
            f"**Additional Cost:** ${option['price_difference']}\n"
            f"**Additional Slots:** +{option['additional_slots']}\n\n"
            f"**Benefits:**\n"
            f"• {option['description']}\n"
            f"• Keep all existing ad slot content\n"
            f"• Seamless upgrade process\n\n"
            f"Would you like to upgrade?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"💎 Upgrade to {option['next_tier'].title()} (+${option['price_difference']})", 
                    callback_data=f"upgrade:{option['next_tier']}"
                )
            ],
            [
                InlineKeyboardButton("⏰ Prolong Current Plan", callback_data="prolong:current"),
                InlineKeyboardButton("📊 My Status", callback_data="cmd:status")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upgrade_subscription: {e}")
        await update.message.reply_text("❌ Error showing upgrade options. Please try again.")

async def prolong_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show prolong options for current subscription."""
    try:
        db = context.bot_data['db']
        user_id = update.effective_user.id
        
        # Get current subscription
        current_subscription = await db.get_user_subscription(user_id)
        
        if not current_subscription or not current_subscription.get('is_active'):
            await update.message.reply_text(
                "❌ You don't have an active subscription to prolong.\n\n"
                "Please subscribe first using /subscribe"
            )
            return
        
        current_tier = current_subscription.get('tier', 'basic')
        expires = current_subscription.get('expires', 'Unknown')
        
        # Define tier prices
        tier_prices = {
            'basic': 15,
            'pro': 45,
            'enterprise': 75
        }
        
        current_price = tier_prices.get(current_tier, 15)
        
        message_text = (
            f"⏰ **Prolong Subscription**\n\n"
            f"**Current Plan:** {current_tier.title()}\n"
            f"**Expires:** {expires}\n"
            f"**Monthly Cost:** ${current_price}\n\n"
            f"**Prolong Options:**\n"
            f"• 30 days: ${current_price}\n"
            f"• 60 days: ${current_price * 2} (save 0%)\n"
            f"• 90 days: ${current_price * 3} (save 0%)\n\n"
            f"Choose how long to prolong your subscription:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("30 Days", callback_data=f"prolong:30"),
                InlineKeyboardButton("60 Days", callback_data=f"prolong:60"),
                InlineKeyboardButton("90 Days", callback_data=f"prolong:90")
            ],
            [
                InlineKeyboardButton("🔄 Upgrade Instead", callback_data="cmd:upgrade_subscription"),
                InlineKeyboardButton("📊 My Status", callback_data="cmd:status")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in prolong_subscription: {e}")
        await update.message.reply_text("❌ Error showing prolong options. Please try again.")

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription upgrade and prolong callbacks."""
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        
        if data.startswith("upgrade:"):
            tier = data.split(":")[1]
            await process_upgrade_payment(update, context, tier)
            
        elif data.startswith("prolong:"):
            duration = data.split(":")[1]
            if duration == "current":
                await prolong_subscription(update, context)
            else:
                await process_prolong_payment(update, context, int(duration))
                
    except Exception as e:
        logger.error(f"Error in handle_subscription_callback: {e}")
        await query.edit_message_text("❌ Error processing request. Please try again.")

async def process_upgrade_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, new_tier: str):
    """Process subscription upgrade payment."""
    try:
        db = context.bot_data['db']
        payment_processor = context.bot_data.get('payment_processor')
        user_id = update.effective_user.id
        
        if not payment_processor:
            await update.callback_query.edit_message_text("❌ Payment system not available")
            return
        
        # Get current subscription
        current_subscription = await db.get_user_subscription(user_id)
        if not current_subscription:
            await update.callback_query.edit_message_text("❌ No active subscription found")
            return
        
        current_tier = current_subscription.get('tier', 'basic')
        
        # Calculate price difference
        tier_prices = {'basic': 15, 'pro': 45, 'enterprise': 75}
        price_difference = tier_prices.get(new_tier, 0) - tier_prices.get(current_tier, 0)
        
        if price_difference <= 0:
            await update.callback_query.edit_message_text("❌ Invalid upgrade request")
            return
        
        # Create payment request
        payment_request = await payment_processor.create_payment_request(
            user_id=user_id,
            tier=f"upgrade_{new_tier}",
            amount_usd=price_difference,
            metadata={
                'upgrade_type': 'tier_upgrade',
                'from_tier': current_tier,
                'to_tier': new_tier,
                'price_difference': price_difference
            }
        )
        
        if payment_request.get('success') is False:
            await update.callback_query.edit_message_text(f"❌ Error creating payment: {payment_request.get('error')}")
            return
        
        # Create payment keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"💳 Pay {payment_request['amount_ton']} TON", 
                    url=payment_request['payment_url']
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Check Payment Status", 
                    callback_data=f"check_upgrade_payment:{payment_request['payment_id']}"
                )
            ],
            [
                InlineKeyboardButton("📊 My Status", callback_data="cmd:status"),
                InlineKeyboardButton("🔙 Back", callback_data="cmd:upgrade_subscription")
            ]
        ]
        
        text = (
            f"💎 **Upgrade to {new_tier.title()}**\n\n"
            f"**Amount:** ${price_difference} ({payment_request['amount_ton']} TON)\n"
            f"**Payment ID:** `{payment_request['payment_id']}`\n\n"
            f"Click the button below to complete your upgrade payment.\n\n"
            f"After payment, your subscription will be automatically upgraded!"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in process_upgrade_payment: {e}")
        await update.callback_query.edit_message_text("❌ Error processing upgrade payment. Please try again.")

async def process_prolong_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    """Process subscription prolong payment."""
    try:
        db = context.bot_data['db']
        payment_processor = context.bot_data.get('payment_processor')
        user_id = update.effective_user.id
        
        if not payment_processor:
            await update.callback_query.edit_message_text("❌ Payment system not available")
            return
        
        # Get current subscription
        current_subscription = await db.get_user_subscription(user_id)
        if not current_subscription:
            await update.callback_query.edit_message_text("❌ No active subscription found")
            return
        
        current_tier = current_subscription.get('tier', 'basic')
        
        # Calculate cost
        tier_prices = {'basic': 15, 'pro': 45, 'enterprise': 75}
        monthly_price = tier_prices.get(current_tier, 15)
        total_cost = (monthly_price * days) / 30  # Pro-rated for days
        
        # Create payment request
        payment_request = await payment_processor.create_payment_request(
            user_id=user_id,
            tier=f"prolong_{current_tier}",
            amount_usd=total_cost,
            metadata={
                'upgrade_type': 'prolong',
                'tier': current_tier,
                'days': days,
                'total_cost': total_cost
            }
        )
        
        if payment_request.get('success') is False:
            await update.callback_query.edit_message_text(f"❌ Error creating payment: {payment_request.get('error')}")
            return
        
        # Create payment keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"💳 Pay {payment_request['amount_ton']} TON", 
                    url=payment_request['payment_url']
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Check Payment Status", 
                    callback_data=f"check_prolong_payment:{payment_request['payment_id']}"
                )
            ],
            [
                InlineKeyboardButton("📊 My Status", callback_data="cmd:status"),
                InlineKeyboardButton("🔙 Back", callback_data="cmd:prolong_subscription")
            ]
        ]
        
        text = (
            f"⏰ **Prolong {current_tier.title()} Subscription**\n\n"
            f"**Duration:** {days} days\n"
            f"**Amount:** ${total_cost:.2f} ({payment_request['amount_ton']} TON)\n"
            f"**Payment ID:** `{payment_request['payment_id']}`\n\n"
            f"Click the button below to complete your payment.\n\n"
            f"After payment, your subscription will be extended by {days} days!"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in process_prolong_payment: {e}")
        await update.callback_query.edit_message_text("❌ Error processing prolong payment. Please try again.")

async def check_upgrade_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    """Check upgrade payment status."""
    try:
        payment_processor = context.bot_data.get('payment_processor')
        db = context.bot_data['db']
        user_id = update.effective_user.id
        
        if not payment_processor:
            await update.callback_query.edit_message_text("❌ Payment system not available")
            return
        
        # Check payment status
        payment_status = await payment_processor.check_payment_status(payment_id)
        
        if payment_status.get('status') == 'completed':
            # Process the upgrade
            payment = await db.get_payment(payment_id)
            if payment and payment.get('metadata'):
                metadata = json.loads(payment.get('metadata', '{}'))
                from_tier = metadata.get('from_tier')
                to_tier = metadata.get('to_tier')
                
                # Perform the upgrade
                success = await db.upgrade_user_subscription(user_id, from_tier, to_tier)
                
                if success:
                    await update.callback_query.edit_message_text(
                        f"🎉 **Upgrade Successful!**\n\n"
                        f"Your subscription has been upgraded from {from_tier.title()} to {to_tier.title()}!\n\n"
                        f"**New Features:**\n"
                        f"• More ad slots available\n"
                        f"• Enhanced posting capabilities\n"
                        f"• Premium support\n\n"
                        f"Use /my_ads to manage your expanded ad slots!"
                    )
                else:
                    await update.callback_query.edit_message_text(
                        "⚠️ Payment received but upgrade failed. Please contact admin."
                    )
            else:
                await update.callback_query.edit_message_text(
                    "⚠️ Payment received but upgrade data missing. Please contact admin."
                )
        elif payment_status.get('status') == 'pending':
            await update.callback_query.edit_message_text(
                "⏳ Payment is still being processed. Please wait a few minutes and check again."
            )
        else:
            await update.callback_query.edit_message_text(
                f"❌ Payment status: {payment_status.get('message', 'Unknown')}"
            )
            
    except Exception as e:
        logger.error(f"Error in check_upgrade_payment_status: {e}")
        await update.callback_query.edit_message_text("❌ Error checking payment status. Please try again.")

async def check_prolong_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
    """Check prolong payment status."""
    try:
        payment_processor = context.bot_data.get('payment_processor')
        db = context.bot_data['db']
        user_id = update.effective_user.id
        
        if not payment_processor:
            await update.callback_query.edit_message_text("❌ Payment system not available")
            return
        
        # Check payment status
        payment_status = await payment_processor.check_payment_status(payment_id)
        
        if payment_status.get('status') == 'completed':
            # Process the prolong
            payment = await db.get_payment(payment_id)
            if payment and payment.get('metadata'):
                metadata = json.loads(payment.get('metadata', '{}'))
                tier = metadata.get('tier')
                days = metadata.get('days')
                
                # Extend the subscription
                success = await db.extend_user_subscription(user_id, tier, days)
                
                if success:
                    await update.callback_query.edit_message_text(
                        f"🎉 **Subscription Extended!**\n\n"
                        f"Your {tier.title()} subscription has been extended by {days} days!\n\n"
                        f"**New Expiry:** Updated automatically\n"
                        f"**Status:** Active and ready to use\n\n"
                        f"Use /my_ads to continue managing your ad slots!"
                    )
                else:
                    await update.callback_query.edit_message_text(
                        "⚠️ Payment received but extension failed. Please contact admin."
                    )
            else:
                await update.callback_query.edit_message_text(
                    "⚠️ Payment received but extension data missing. Please contact admin."
                )
        elif payment_status.get('status') == 'pending':
            await update.callback_query.edit_message_text(
                "⏳ Payment is still being processed. Please wait a few minutes and check again."
            )
        else:
            await update.callback_query.edit_message_text(
                f"❌ Payment status: {payment_status.get('message', 'Unknown')}"
            )
            
    except Exception as e:
        logger.error(f"Error in check_prolong_payment_status: {e}")
        await update.callback_query.edit_message_text("❌ Error checking payment status. Please try again.")
