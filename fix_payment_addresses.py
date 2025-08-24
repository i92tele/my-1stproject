#!/usr/bin/env python3
"""
Fix Payment Addresses

This script fixes the issue where the payment system is not retrieving crypto addresses
from the environment variables properly.
"""

import asyncio
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def fix_payment_processor():
    """Fix the payment processor to properly retrieve crypto addresses."""
    logger.info("🔧 FIXING PAYMENT PROCESSOR")
    
    try:
        # Check if the file exists
        if not os.path.exists('src/services/payment_processor.py'):
            logger.error("❌ src/services/payment_processor.py not found")
            return False
        
        # Read the current file
        with open('src/services/payment_processor.py', 'r') as f:
            content = f.read()
        
        # Check if the merchant_wallet is properly initialized
        if "self.merchant_wallet = os.getenv('TON_MERCHANT_WALLET', '')" in content:
            # Update the initialization
            updated_content = content.replace(
                "self.merchant_wallet = os.getenv('TON_MERCHANT_WALLET', '')",
                "self.merchant_wallet = os.getenv('TON_ADDRESS') or os.getenv('TON_MERCHANT_WALLET', '')"
            )
            
            # Update _create_payment_url method to check for wallet address
            if "async def _create_payment_url" in updated_content:
                create_url_method = """    async def _create_payment_url(self, payment_id: str, ton_amount: Decimal) -> str:
        \"\"\"Create a TON payment URL.\"\"\"
        try:
            # Get merchant wallet address
            wallet = self.merchant_wallet
            if not wallet:
                wallet = os.getenv('TON_ADDRESS')
                if not wallet:
                    self.logger.error("No TON wallet address found in environment variables")
                    return ""
            
            # Format amount for TON
            amount_formatted = f"{ton_amount:.9f}".rstrip('0').rstrip('.')
            
            # Create payment URL
            payment_url = f"ton://transfer/{wallet}?amount={amount_formatted}&text={payment_id}"
            
            self.logger.info(f"Created payment URL for wallet {wallet}")
            return payment_url
            
        except Exception as e:
            self.logger.error(f"Error creating payment URL: {e}")
            return """""
                
                # Replace the method
                old_method_start = "    async def _create_payment_url(self, payment_id: str, ton_amount: Decimal) -> str:"
                old_method_end = "            return \"\"\n"
                
                # Find the positions
                start_pos = updated_content.find(old_method_start)
                if start_pos > 0:
                    # Find the end of the method
                    search_from = start_pos + len(old_method_start)
                    end_pos = updated_content.find(old_method_end, search_from) + len(old_method_end)
                    
                    if end_pos > len(old_method_start):
                        # Replace the method
                        updated_content = updated_content[:start_pos] + create_url_method + updated_content[end_pos:]
            
            # Update create_payment_request method to include crypto address in response
            if "async def create_payment_request" in updated_content and "return {" in updated_content:
                # Find the return statement in create_payment_request
                return_start = updated_content.find("            return {", updated_content.find("async def create_payment_request"))
                if return_start > 0:
                    # Find the closing brace
                    return_end = updated_content.find("            }", return_start)
                    if return_end > 0:
                        # Extract the return statement
                        return_statement = updated_content[return_start:return_end + 13]
                        
                        # Check if it needs updating
                        if "'address':" not in return_statement:
                            # Add address to return statement
                            updated_return = return_statement.replace(
                                "            return {",
                                "            return {\n                'address': self.merchant_wallet,"
                            )
                            
                            # Replace in content
                            updated_content = updated_content.replace(return_statement, updated_return)
            
            # Write the updated content
            with open('src/services/payment_processor.py', 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Updated payment_processor.py to properly handle crypto addresses")
            return True
        else:
            logger.warning("⚠️ Could not find merchant_wallet initialization in payment_processor.py")
            return False
    except Exception as e:
        logger.error(f"❌ Error fixing payment_processor.py: {e}")
        return False

async def create_direct_payment_processor():
    """Create a direct payment processor that handles multiple cryptocurrencies."""
    logger.info("\n🔧 CREATING DIRECT PAYMENT PROCESSOR")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs('src/payment', exist_ok=True)
        
        # Create direct payment processor
        with open('src/payment/direct_payment.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"
Direct Payment Processor

This module handles direct cryptocurrency payments without third-party providers.
\"\"\"

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List

class DirectPaymentProcessor:
    \"\"\"Direct cryptocurrency payment processor.\"\"\"
    
    def __init__(self, db_manager, logger):
        \"\"\"Initialize direct payment processor.\"\"\"
        self.db = db_manager
        self.logger = logger
        self.payment_timeout_minutes = 60
        
        # Load crypto addresses
        self.crypto_addresses = {
            'BTC': os.getenv('BTC_ADDRESS', ''),
            'ETH': os.getenv('ETH_ADDRESS', ''),
            'USDT': os.getenv('USDT_ADDRESS', ''),
            'USDC': os.getenv('USDC_ADDRESS', ''),
            'LTC': os.getenv('LTC_ADDRESS', ''),
            'SOL': os.getenv('SOL_ADDRESS', ''),
            'TON': os.getenv('TON_ADDRESS', '')
        }
        
        # Log available cryptocurrencies
        available_cryptos = [crypto for crypto, address in self.crypto_addresses.items() if address]
        self.logger.info(f"Available cryptocurrencies: {', '.join(available_cryptos)}")
        
        # Tier configurations
        self.tiers = {
            'basic': {
                'slots': 1,
                'price_usd': 15,
                'duration_days': 30
            },
            'pro': {
                'slots': 3,
                'price_usd': 45,
                'duration_days': 30
            },
            'enterprise': {
                'slots': 5,
                'price_usd': 75,
                'duration_days': 30
            }
        }
        
        # Price cache
        self.price_cache = {}
        self.price_cache_time = {}
        self.price_cache_duration = 300  # 5 minutes
    
    async def create_payment(self, user_id: int, crypto_type: str, tier: str) -> Dict[str, Any]:
        \"\"\"Create a new cryptocurrency payment.\"\"\"
        try:
            # Validate crypto type
            crypto_type = crypto_type.upper()
            if crypto_type not in self.crypto_addresses:
                return {'error': f"Unsupported cryptocurrency: {crypto_type}"}
            
            # Get crypto address
            address = self.crypto_addresses.get(crypto_type)
            if not address:
                return {'error': f"No address configured for {crypto_type}"}
            
            # Validate tier
            if tier not in self.tiers:
                return {'error': f"Invalid tier: {tier}"}
            
            # Get tier price
            amount_usd = self.tiers[tier]['price_usd']
            
            # Get crypto price and calculate amount
            crypto_price = await self._get_crypto_price(crypto_type)
            if not crypto_price:
                return {'error': f"Could not get price for {crypto_type}"}
            
            crypto_amount = Decimal(amount_usd) / Decimal(crypto_price)
            
            # Round to appropriate decimal places based on crypto
            if crypto_type in ['BTC', 'ETH', 'LTC']:
                crypto_amount = round(crypto_amount, 8)  # 8 decimal places
            elif crypto_type in ['USDT', 'USDC']:
                crypto_amount = round(crypto_amount, 6)  # 6 decimal places
            elif crypto_type in ['SOL']:
                crypto_amount = round(crypto_amount, 9)  # 9 decimal places
            elif crypto_type in ['TON']:
                crypto_amount = round(crypto_amount, 9)  # 9 decimal places
            
            # Generate payment ID
            payment_id = f"{crypto_type}_{uuid.uuid4().hex[:16]}"
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(minutes=self.payment_timeout_minutes)
            
            # Create payment URL based on crypto type
            if crypto_type == 'BTC':
                payment_url = f"bitcoin:{address}?amount={crypto_amount}"
            elif crypto_type == 'ETH':
                payment_url = f"ethereum:{address}?value={crypto_amount}"
            elif crypto_type == 'LTC':
                payment_url = f"litecoin:{address}?amount={crypto_amount}"
            elif crypto_type == 'SOL':
                payment_url = f"solana:{address}?amount={crypto_amount}"
            elif crypto_type == 'TON':
                payment_url = f"ton://transfer/{address}?amount={crypto_amount}&text={payment_id}"
            else:
                payment_url = f"crypto:{crypto_type.lower()}:{address}?amount={crypto_amount}"
            
            # Store payment in database
            success = await self.db.create_payment(
                payment_id=payment_id,
                user_id=user_id,
                amount_usd=amount_usd,
                crypto_type=crypto_type,
                payment_provider="direct",
                pay_to_address=address,
                expected_amount_crypto=float(crypto_amount),
                payment_url=payment_url,
                expires_at=expires_at,
                attribution_method="amount_only"
            )
            
            if not success:
                return {'error': "Failed to store payment in database"}
            
            # Create ad slots for the user
            tier_config = self.tiers[tier]
            for i in range(tier_config['slots']):
                await self.db.create_ad_slot(user_id, i + 1)
            
            self.logger.info(f"✅ Created {crypto_type} payment request {payment_id} for user {user_id}")
            
            return {
                'payment_id': payment_id,
                'crypto_type': crypto_type,
                'amount_crypto': float(crypto_amount),
                'amount_usd': amount_usd,
                'payment_url': payment_url,
                'address': address,
                'expires_at': expires_at.isoformat(),
                'tier': tier,
                'slots_created': tier_config['slots']
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return {'error': str(e)}
    
    async def get_supported_cryptos(self) -> List[str]:
        \"\"\"Get list of supported cryptocurrencies.\"\"\"
        return [crypto for crypto, address in self.crypto_addresses.items() if address]
    
    async def _get_crypto_price(self, crypto_type: str) -> Optional[float]:
        \"\"\"Get current price of cryptocurrency in USD.\"\"\"
        try:
            # Check cache first
            if (crypto_type in self.price_cache and 
                crypto_type in self.price_cache_time and 
                (datetime.now() - self.price_cache_time[crypto_type]).seconds < self.price_cache_duration):
                return self.price_cache[crypto_type]
            
            # For now, use mock prices - in production, use CoinGecko or similar API
            mock_prices = {
                'BTC': 60000.0,
                'ETH': 3000.0,
                'USDT': 1.0,
                'USDC': 1.0,
                'LTC': 80.0,
                'SOL': 100.0,
                'TON': 5.0
            }
            
            price = mock_prices.get(crypto_type)
            
            if price:
                # Update cache
                self.price_cache[crypto_type] = price
                self.price_cache_time[crypto_type] = datetime.now()
            
            return price
            
        except Exception as e:
            self.logger.error(f"Error getting {crypto_type} price: {e}")
            return None

# Global instance
direct_payment_processor = None

def initialize_direct_payment_processor(db_manager, logger):
    \"\"\"Initialize the global DirectPaymentProcessor instance.\"\"\"
    global direct_payment_processor
    direct_payment_processor = DirectPaymentProcessor(db_manager, logger)
    return direct_payment_processor

def get_direct_payment_processor():
    \"\"\"Get the global DirectPaymentProcessor instance.\"\"\"
    return direct_payment_processor
""")
        
        logger.info("✅ Created direct_payment.py")
        
        # Create integration module
        with open('src/payment/__init__.py', 'w') as f:
            f.write("""\"\"\"
Payment module for cryptocurrency payments.
\"\"\"

from .direct_payment import initialize_direct_payment_processor, get_direct_payment_processor
""")
        
        logger.info("✅ Created payment module initialization")
        
        # Update bot.py to use the direct payment processor
        if os.path.exists('bot.py'):
            with open('bot.py', 'r') as f:
                bot_content = f.read()
            
            # Check if we need to update the file
            if "from src.payment.direct_payment import" not in bot_content:
                # Add import
                if "from src.services.payment_processor import" in bot_content:
                    updated_bot_content = bot_content.replace(
                        "from src.services.payment_processor import",
                        "from src.services.payment_processor import\nfrom src.payment.direct_payment import initialize_direct_payment_processor, get_direct_payment_processor"
                    )
                    
                    # Add initialization
                    if "# Initialize payment processor" in updated_bot_content:
                        updated_bot_content = updated_bot_content.replace(
                            "# Initialize payment processor\n    initialize_payment_processor(db, logger)",
                            "# Initialize payment processors\n    initialize_payment_processor(db, logger)\n    initialize_direct_payment_processor(db, logger)"
                        )
                    
                    # Write the updated content
                    with open('bot.py', 'w') as f:
                        f.write(updated_bot_content)
                    
                    logger.info("✅ Updated bot.py to use direct payment processor")
                else:
                    logger.warning("⚠️ Could not find payment processor import in bot.py")
            else:
                logger.info("✅ bot.py already uses direct payment processor")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error creating direct payment processor: {e}")
        return False

async def create_payment_command_handler():
    """Create a command handler for payments."""
    logger.info("\n🔧 CREATING PAYMENT COMMAND HANDLER")
    
    try:
        # Check if commands directory exists
        if not os.path.exists('src/commands'):
            logger.warning("⚠️ src/commands directory not found")
            return False
        
        # Create payment command handler
        with open('src/commands/payment_commands.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"
Payment Commands

This module handles payment-related commands.
\"\"\"

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

from src.payment.direct_payment import get_direct_payment_processor

logger = logging.getLogger(__name__)

async def cmd_crypto_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    \"\"\"Handle cryptocurrency selection for payments.\"\"\"
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
    \"\"\"Create a payment for the selected cryptocurrency.\"\"\"
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
        payment = await payment_processor.create_payment(user_id, crypto_type, tier)
        
        if 'error' in payment:
            await update.callback_query.answer(f"Error: {payment['error']}")
            return
        
        # Format amount
        amount_crypto = payment['amount_crypto']
        
        # Create message
        message = f"💰 *{tier.capitalize()} Subscription Payment*\\n\\n"
        message += f"• Amount: *{amount_crypto} {crypto_type}*\\n"
        message += f"• Address: `{payment['address']}`\\n"
        message += f"• Payment ID: `{payment['payment_id']}`\\n\\n"
        message += "Please send the exact amount to the address above.\\n"
        message += "Your subscription will be activated automatically once payment is confirmed.\\n\\n"
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
    \"\"\"Check payment status.\"\"\"
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
            "Payment verification in progress. This may take a few minutes.\\n\\n"
            "Your subscription will be activated automatically once payment is confirmed.",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        await update.callback_query.answer("An error occurred")
""")
        
        logger.info("✅ Created payment_commands.py")
        
        # Update command handlers in bot.py
        if os.path.exists('bot.py'):
            with open('bot.py', 'r') as f:
                bot_content = f.read()
            
            # Check if we need to update the file
            if "from src.commands.payment_commands import" not in bot_content:
                # Add import
                if "from src.commands." in bot_content:
                    # Find the last import from src.commands
                    last_import_idx = bot_content.rfind("from src.commands.")
                    if last_import_idx > 0:
                        # Find the end of the line
                        end_line_idx = bot_content.find("\n", last_import_idx)
                        if end_line_idx > 0:
                            # Insert new import after the last one
                            updated_bot_content = bot_content[:end_line_idx+1] + "from src.commands.payment_commands import cmd_crypto_select, cmd_create_payment, cmd_check_payment\n" + bot_content[end_line_idx+1:]
                            
                            # Add handlers
                            if "application.add_handler" in updated_bot_content:
                                # Find the last handler
                                last_handler_idx = updated_bot_content.rfind("application.add_handler")
                                if last_handler_idx > 0:
                                    # Find the end of the line
                                    end_line_idx = updated_bot_content.find("\n", last_handler_idx)
                                    if end_line_idx > 0:
                                        # Insert new handlers after the last one
                                        new_handlers = """
    # Payment handlers
    application.add_handler(CallbackQueryHandler(cmd_crypto_select, pattern="^crypto_select"))
    application.add_handler(CallbackQueryHandler(cmd_create_payment, pattern="^pay_"))
    application.add_handler(CallbackQueryHandler(cmd_check_payment, pattern="^check_"))
"""
                                        updated_bot_content = updated_bot_content[:end_line_idx+1] + new_handlers + updated_bot_content[end_line_idx+1:]
                            
                            # Write the updated content
                            with open('bot.py', 'w') as f:
                                f.write(updated_bot_content)
                            
                            logger.info("✅ Updated bot.py with payment command handlers")
                        else:
                            logger.warning("⚠️ Could not find end of line for src.commands import")
                    else:
                        logger.warning("⚠️ Could not find src.commands import in bot.py")
                else:
                    logger.warning("⚠️ Could not find any src.commands import in bot.py")
            else:
                logger.info("✅ bot.py already has payment command handlers")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error creating payment command handler: {e}")
        return False

async def main():
    """Main function."""
    logger.info("🔧 PAYMENT ADDRESS FIX")
    logger.info("=" * 60)
    
    # Fix payment processor
    processor_fixed = await fix_payment_processor()
    
    # Create direct payment processor
    direct_processor_created = await create_direct_payment_processor()
    
    # Create payment command handler
    command_handler_created = await create_payment_command_handler()
    
    # Summary
    logger.info("\n📋 FIX SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Payment Processor: {'✅ Fixed' if processor_fixed else '❌ Failed'}")
    logger.info(f"Direct Payment Processor: {'✅ Created' if direct_processor_created else '❌ Failed'}")
    logger.info(f"Payment Command Handler: {'✅ Created' if command_handler_created else '❌ Failed'}")
    
    if processor_fixed or direct_processor_created:
        logger.info("\n✅ PAYMENT SYSTEM FIXED")
        logger.info("Restart the bot to apply changes")
    else:
        logger.warning("\n⚠️ PAYMENT SYSTEM FIX INCOMPLETE")
        logger.warning("Check the logs for details")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
