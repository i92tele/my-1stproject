from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from typing import List, Dict, Optional

class EnhancedUI:
    """User interface components."""

    def __init__(self, config):
        self.config = config

    def get_main_menu_keyboard(self, user_data: Dict) -> ReplyKeyboardMarkup:
        """Create main menu keyboard based on user status."""
        has_subscription = user_data.get('has_subscription', False)

        if has_subscription:
            keyboard = [
                ['Forward Message', 'My Destinations'],
                ['Status', 'Settings'],
                ['Help']
            ]
        else:
            keyboard = [
                ['Subscribe Now', 'How It Works'],
                ['Pricing', 'Support']
            ]

        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

    def get_subscription_keyboard(self, current_tier: Optional[str] = None) -> InlineKeyboardMarkup:
        """Create subscription selection keyboard."""
        keyboard = []

        for tier_id, tier_info in self.config.subscription_tiers.items():
            if current_tier == tier_id:
                button_text = f"✅ {tier_id.title()} (Current)"
            else:
                button_text = f"{tier_id.title()} - ${tier_info['price']}/mo"

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"view_tier:{tier_id}"
            )])

        keyboard.append([InlineKeyboardButton("Back", callback_data="main_menu")])

        return InlineKeyboardMarkup(keyboard)

    def format_tier_details(self, tier: str) -> str:
        """Format detailed tier information."""
        tier_info = self.config.get_tier_info(tier)
        if not tier_info:
            return "Invalid tier"

        details = {
            'basic': {
                'icon': 'Basic',
                'features': [
                    '✅ Forward to 3 destinations',
                    '✅ 1,000 messages/day',
                    '✅ Basic filters',
                    '✅ Email support'
                ]
            },
            'premium': {
                'icon': 'Premium',
                'features': [
                    '✅ Forward to 10 destinations',
                    '✅ 10,000 messages/day',
                    '✅ Advanced filters',
                    '✅ Priority support',
                    '✅ Message scheduling'
                ]
            },
            'pro': {
                'icon': 'Professional',
                'features': [
                    '✅ Unlimited destinations',
                    '✅ Unlimited messages',
                    '✅ All features included',
                    '✅ VIP 24/7 support',
                    '✅ API access',
                    '✅ Custom features'
                ]
            }
        }

        tier_detail = details.get(tier, {})
        icon = tier_detail.get('icon', 'Plan')
        features = tier_detail.get('features', [])

        text = (
            f"*{icon} Plan*\n"
            f"Price: *${tier_info['price']}/month*\n\n"
            f"*Features:*\n"
            f"{chr(10).join(features)}\n\n"
            f"Ready to subscribe? Choose your payment method below:"
        )

        return text

    def get_payment_method_keyboard(self, tier: str) -> InlineKeyboardMarkup:
        """Create payment method selection keyboard."""
        keyboard = [
            [InlineKeyboardButton("Bitcoin", callback_data=f"pay:{tier}:bitcoin")],
            [InlineKeyboardButton("Ethereum", callback_data=f"pay:{tier}:ethereum")],
            [InlineKeyboardButton("Solana", callback_data=f"pay:{tier}:solana")],
            [InlineKeyboardButton("Litecoin", callback_data=f"pay:{tier}:litecoin")],
            [InlineKeyboardButton("Back", callback_data=f"view_tier:{tier}")]
        ]

        return InlineKeyboardMarkup(keyboard)

    def format_payment_instructions(self, payment_data: Dict) -> str:
        """Format payment instructions."""
        crypto_symbols = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'solana': 'SOL',
            'litecoin': 'LTC'
        }

        symbol = crypto_symbols.get(payment_data['cryptocurrency'], '')

        text = (
            f"*Payment Details*\n\n"
            f"*Amount:* `{payment_data['amount_crypto']} {symbol}` (${payment_data['amount_usd']})\n"
            f"*Cryptocurrency:* {payment_data['cryptocurrency'].title()}\n"
            f"*Payment ID:* `{payment_data['payment_memo']}`\n\n"
            f"*Send to address:*\n"
            f"`{payment_data['wallet_address']}`\n\n"
            f"*Important:*\n"
            f"• Include the Payment ID in the transaction memo/note\n"
            f"• Payment expires in 2 hours\n"
            f"• After sending, contact admin with transaction hash\n\n"
            f"Scan the QR code or copy the address above to complete payment."
        )

        return text

    def get_destinations_keyboard(self, destinations: List[Dict]) -> InlineKeyboardMarkup:
        """Create destinations management keyboard."""
        keyboard = []

        for dest in destinations[:10]:
            icon = "Channel" if dest['destination_type'] == 'channel' else "Group"
            button_text = f"{icon}: {dest['destination_name'][:30]}"
            callback_data = f"dest:{dest['id']}"

            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        action_buttons = []
        if len(destinations) < 10:
            action_buttons.append(InlineKeyboardButton("Add New", callback_data="add_destination"))

        if action_buttons:
            keyboard.append(action_buttons)

        keyboard.append([InlineKeyboardButton("Back", callback_data="main_menu")])

        return InlineKeyboardMarkup(keyboard)

    def format_welcome_message(self, user_name: str) -> str:
        """Format welcome message for new users."""
        return (
            f"Welcome to *{self.config.bot_name}*, {user_name}!\n\n"
            f"I'm your personal message forwarding assistant. I can automatically forward "
            f"your messages to multiple channels and groups with powerful filtering options.\n\n"
            f"*Quick Start:*\n"
            f"1. Subscribe to a plan with /subscribe\n"
            f"2. Add destinations with /add_destination\n"
            f"3. Send messages to forward them automatically!\n\n"
            f"*Features:*\n"
            f"- Forward to multiple destinations\n"
            f"- Filter by keywords\n"
            f"- Support for all message types\n"
            f"- Reliable and fast\n\n"
            f"Ready to get started? Use /subscribe to choose a plan!"
        )
