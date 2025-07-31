#!/usr/bin/env python3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

class EnhancedUI:
    """Enhanced UI with professional styling inspired by AutoADS."""
    
    @staticmethod
    def create_welcome_message(user_name: str, subscription_info: Dict = None) -> str:
        """Create a professional welcome message with rocket branding."""
        message = f"""
🚀 **AutoFarming Pro**
*#1 Automated Ad Posting Service*

Welcome back, {user_name}! 👋

"""
        
        if subscription_info:
            tier_emoji = {"basic": "🥉", "pro": "🥈", "enterprise": "🥇"}
            tier = subscription_info.get('tier', 'basic')
            days_left = subscription_info.get('days_left', 0)
            
            message += f"""
**Your Subscription:**
{tier_emoji.get(tier, "📊")} {tier.title()} - {days_left} days remaining

"""
        else:
            message += """
**Get Started:**
Choose a subscription plan to start automating your ads!

"""
        
        message += """
*Why Choose AutoFarming Pro?*
• 🚀 Hourly automated posting
• 🤖 Fully customized bots  
• 💰 Competitive pricing
• 📊 Advanced analytics
• 🛡️ Ban protection
• ⚡ 24/7 support
"""
        
        return message
    
    @staticmethod
    def create_subscription_keyboard() -> InlineKeyboardMarkup:
        """Create subscription tier selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🥉 Basic - $9.99", callback_data="subscribe:basic"),
                InlineKeyboardButton("🥈 Pro - $19.99", callback_data="subscribe:pro")
            ],
            [
                InlineKeyboardButton("🥇 Enterprise - $29.99", callback_data="subscribe:enterprise")
            ],
            [
                InlineKeyboardButton("📊 Compare Plans", callback_data="compare_plans"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_tier_details_message(tier: str, tier_info: Dict) -> str:
        """Create detailed tier information message."""
        price = tier_info.get('price', 0)
        features = tier_info.get('features', [])
        ad_slots = tier_info.get('ad_slots', 1)
        
        tier_names = {"basic": "Basic", "pro": "Pro", "enterprise": "Enterprise"}
        tier_emojis = {"basic": "🥉", "pro": "🥈", "enterprise": "🥇"}
        
        message = f"""
{tier_emojis.get(tier, "📊")} **{tier_names.get(tier, tier.title())} - ${price}/Month**

**What's Included:**
"""
        
        for feature in features:
            message += f"• {feature}\n"
        
        message += f"""
**Plan Details:**
• 📊 Ad Slots: {ad_slots}
• ⏰ Duration: 30 days
• 🔄 Auto-renewal: {'Yes' if tier == 'enterprise' else 'No'}

*Ready to get started? Choose your payment method below!*
"""
        
        return message
    
    @staticmethod
    def create_payment_methods_keyboard(tier: str) -> InlineKeyboardMarkup:
        """Create payment method selection keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("💎 TON", callback_data=f"pay:{tier}:ton"),
                InlineKeyboardButton("₿ Bitcoin", callback_data=f"pay:{tier}:btc")
            ],
            [
                InlineKeyboardButton("Ξ Ethereum", callback_data=f"pay:{tier}:eth"),
                InlineKeyboardButton("💵 USDT", callback_data=f"pay:{tier}:usdt")
            ],
            [
                InlineKeyboardButton("◎ Solana", callback_data=f"pay:{tier}:sol"),
                InlineKeyboardButton("Ł Litecoin", callback_data=f"pay:{tier}:ltc")
            ],
            [
                InlineKeyboardButton("🔙 Back to Plans", callback_data="back_to_plans")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_ad_management_message(user_id: int, ad_slots: List[Dict]) -> str:
        """Create enhanced ad management message."""
        message = f"""
🎯 **Ad Management Dashboard**

**Your Ad Slots:**
"""
        
        for i, slot in enumerate(ad_slots, 1):
            status = "🟢 Active" if slot.get('is_active') else "🔴 Inactive"
            content = slot.get('ad_content', 'Not set')
            destinations = len(slot.get('destinations', []))
            
            message += f"""
**Slot {i}** {status}
📝 Content: {content[:50]}{'...' if len(content) > 50 else ''}
🎯 Destinations: {destinations} groups
⏰ Interval: {slot.get('interval_minutes', 60)} minutes
"""
        
        message += """
*Click on a slot to manage it!*
"""
        
        return message
    
    @staticmethod
    def create_ad_slot_keyboard(slot_id: int, slot_info: Dict) -> InlineKeyboardMarkup:
        """Create ad slot management keyboard."""
        status = "🟢 Active" if slot_info.get('is_active') else "🔴 Inactive"
        toggle_text = "🔴 Deactivate" if slot_info.get('is_active') else "🟢 Activate"
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Set Content", callback_data=f"set_content:{slot_id}"),
                InlineKeyboardButton("🎯 Set Destinations", callback_data=f"set_dests:{slot_id}")
            ],
            [
                InlineKeyboardButton("⏰ Set Schedule", callback_data=f"set_schedule:{slot_id}"),
                InlineKeyboardButton(toggle_text, callback_data=f"toggle_ad:{slot_id}")
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data=f"slot_analytics:{slot_id}"),
                InlineKeyboardButton("🔙 Back to Slots", callback_data="back_to_slots")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_analytics_message(stats: Dict) -> str:
        """Create enhanced analytics message."""
        message = f"""
📊 **Analytics Dashboard**

**Overall Performance:**
• 📈 Total Posts: {stats.get('total_posts', 0)}
• 👥 Total Views: {stats.get('total_views', 0)}
• 🎯 Success Rate: {stats.get('success_rate', 0)}%
• 💰 Revenue: ${stats.get('revenue', 0):.2f}

**This Month:**
• 📅 Posts: {stats.get('monthly_posts', 0)}
• 📈 Growth: {stats.get('growth_rate', 0)}%
• 🎯 Engagement: {stats.get('engagement_rate', 0)}%

**Top Performing Groups:**
"""
        
        top_groups = stats.get('top_groups', [])
        for i, group in enumerate(top_groups[:5], 1):
            message += f"{i}. {group.get('name', 'Unknown')} - {group.get('views', 0)} views\n"
        
        return message
    
    @staticmethod
    def create_status_badge(subscription_info: Dict) -> str:
        """Create subscription status badge."""
        if not subscription_info:
            return "🔴 No Subscription"
        
        tier = subscription_info.get('tier', 'basic')
        days_left = subscription_info.get('days_left', 0)
        
        tier_emojis = {"basic": "🥉", "pro": "🥈", "enterprise": "🥇"}
        status_emoji = "🟢" if days_left > 0 else "🔴"
        
        return f"{status_emoji} {tier_emojis.get(tier, '📊')} {tier.title()} - {days_left} days"
    
    @staticmethod
    def create_error_message(error: str) -> str:
        """Create user-friendly error message."""
        return f"""
❌ **Oops! Something went wrong**

{error}

Please try again or contact support if the problem persists.
"""
    
    @staticmethod
    def create_success_message(action: str) -> str:
        """Create success confirmation message."""
        return f"""
✅ **Success!**

{action} has been completed successfully.

You can continue using the bot or check your dashboard for updates.
"""
