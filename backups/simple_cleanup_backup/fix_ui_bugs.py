#!/usr/bin/env python3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

class UIBugFix:
    """Critical fixes for UI bugs and callback data issues."""
    
    @staticmethod
    def truncate_callback_data(data: str, max_length: int = 64) -> str:
        """Ensure callback data doesn't exceed Telegram's 64-byte limit."""
        if len(data) <= max_length:
            return data
        
        # If data is too long, create a shorter version
        # Keep the essential parts and truncate the rest
        parts = data.split(':')
        if len(parts) >= 2:
            # Keep the action and essential ID, truncate the rest
            action = parts[0]
            essential_id = parts[1][:20]  # Keep first 20 chars of ID
            return f"{action}:{essential_id}"
        else:
            # If no separator, just truncate
            return data[:max_length]
    
    @staticmethod
    def split_long_message(text: str, max_length: int = 4000) -> List[str]:
        """Split long messages to avoid Telegram's 4096 character limit."""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        current_message = ""
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_message) + len(paragraph) + 2 > max_length:
                if current_message:
                    messages.append(current_message.strip())
                    current_message = paragraph
                else:
                    # Single paragraph is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_message) + len(sentence) + 2 > max_length:
                            if current_message:
                                messages.append(current_message.strip())
                                current_message = sentence
                            else:
                                # Single sentence is too long, split by words
                                words = sentence.split(' ')
                                for word in words:
                                    if len(current_message) + len(word) + 1 > max_length:
                                        if current_message:
                                            messages.append(current_message.strip())
                                            current_message = word
                                        else:
                                            # Single word is too long, truncate
                                            messages.append(word[:max_length])
                                    else:
                                        current_message += " " + word if current_message else word
                        else:
                            current_message += ". " + sentence if current_message else sentence
            else:
                current_message += "\n\n" + paragraph if current_message else paragraph
        
        if current_message:
            messages.append(current_message.strip())
        
        return messages
    
    @staticmethod
    def create_safe_keyboard(buttons: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
        """Create keyboard with safe callback data."""
        safe_buttons = []
        for row in buttons:
            safe_row = []
            for button in row:
                # Truncate callback data if needed
                safe_callback = UIBugFix.truncate_callback_data(button.callback_data)
                safe_button = InlineKeyboardButton(button.text, callback_data=safe_callback)
                safe_row.append(safe_button)
            safe_buttons.append(safe_row)
        return InlineKeyboardMarkup(safe_buttons)
    
    @staticmethod
    def create_enhanced_welcome_message(user_name: str, subscription_info: Dict = None) -> str:
        """Create enhanced welcome message with proper formatting."""
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
    def create_enhanced_subscription_keyboard() -> InlineKeyboardMarkup:
        """Create enhanced subscription keyboard with safe callback data."""
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
        return UIBugFix.create_safe_keyboard(keyboard)
    
    @staticmethod
    def create_enhanced_ad_slot_keyboard(slot_id: int, slot_info: Dict) -> InlineKeyboardMarkup:
        """Create enhanced ad slot keyboard with safe callback data."""
        is_active = slot_info.get('is_active', False)
        
        keyboard = [
            [InlineKeyboardButton("📝 Set Ad Content", callback_data=f"set_content:{slot_id}")],
            [InlineKeyboardButton("🗓️ Set Schedule", callback_data=f"set_schedule:{slot_id}")],
            [InlineKeyboardButton("🎯 Set Destinations", callback_data=f"set_dests:{slot_id}")],
            [InlineKeyboardButton("⏸️ Pause Ad" if is_active else "▶️ Resume Ad", callback_data=f"toggle_ad:{slot_id}")],
            [InlineKeyboardButton("⬅️ Back to All Slots", callback_data="back_to_slots")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")]
        ]
        return UIBugFix.create_safe_keyboard(keyboard)
    
    @staticmethod
    def create_enhanced_payment_keyboard(tier: str) -> InlineKeyboardMarkup:
        """Create enhanced payment keyboard with safe callback data."""
        keyboard = [
            [InlineKeyboardButton("💎 Pay with TON", callback_data=f"pay:{tier}:ton")],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data="cmd:subscribe")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="cmd:start")]
        ]
        return UIBugFix.create_safe_keyboard(keyboard)
    
    @staticmethod
    def create_enhanced_error_message(error_type: str, details: str = "") -> str:
        """Create user-friendly error messages."""
        error_messages = {
            "payment_failed": "❌ Payment failed. Please try again or contact support.",
            "worker_unavailable": "⚠️ Service temporarily unavailable. Please try again in a few minutes.",
            "database_error": "🔧 Technical issue detected. Our team has been notified.",
            "permission_denied": "🚫 You don't have permission to perform this action.",
            "invalid_input": "📝 Please check your input and try again.",
            "timeout": "⏰ Request timed out. Please try again.",
            "network_error": "🌐 Network error. Please check your connection and try again."
        }
        
        base_message = error_messages.get(error_type, "❌ An error occurred. Please try again.")
        
        if details:
            return f"{base_message}\n\n*Details:* {details}"
        
        return base_message
    
    @staticmethod
    def create_enhanced_success_message(action: str) -> str:
        """Create user-friendly success messages."""
        success_messages = {
            "payment_successful": "✅ Payment successful! Your subscription is now active.",
            "ad_created": "✅ Ad created successfully! It will start posting according to your schedule.",
            "settings_updated": "✅ Settings updated successfully!",
            "subscription_activated": "✅ Subscription activated! You can now create ads.",
            "content_saved": "✅ Content saved successfully!",
            "schedule_updated": "✅ Schedule updated successfully!",
            "destinations_set": "✅ Destinations set successfully!"
        }
        
        return success_messages.get(action, "✅ Operation completed successfully!")
    
    @staticmethod
    def validate_message_length(text: str, max_length: int = 4000) -> bool:
        """Validate if message length is within limits."""
        return len(text) <= max_length
    
    @staticmethod
    def validate_callback_data(data: str, max_length: int = 64) -> bool:
        """Validate if callback data is within limits."""
        return len(data) <= max_length
    
    @staticmethod
    def create_progress_message(current: int, total: int, action: str) -> str:
        """Create progress message for long operations."""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
        
        return f"""
🔄 **{action}**

Progress: {current}/{total} ({percentage:.1f}%)
{progress_bar}

Please wait...
"""
    
    @staticmethod
    def create_help_message() -> str:
        """Create comprehensive help message."""
        return """
📚 **AutoFarming Pro - Help Guide**

**Getting Started:**
1. Choose a subscription plan
2. Complete payment with TON
3. Create your first ad
4. Set posting schedule
5. Select target groups

**Available Commands:**
• /start - Main menu
• /my_ads - Manage your ads
• /analytics - View performance
• /subscribe - Subscription plans
• /help - This help message

**Features:**
• 🚀 Automated posting
• 📊 Performance analytics
• 🛡️ Ban protection
• ⚡ 24/7 operation
• 💰 Competitive pricing

**Need Support?**
Contact our team for assistance.
"""

def main():
    """Test the UI bug fixes."""
    # Test callback data truncation
    long_callback = "very_long_callback_data_that_exceeds_telegram_limit_of_64_bytes"
    truncated = UIBugFix.truncate_callback_data(long_callback)
    print(f"Original: {long_callback}")
    print(f"Truncated: {truncated}")
    print(f"Length: {len(truncated)} bytes")
    
    # Test message splitting
    long_message = "This is a very long message. " * 200
    split_messages = UIBugFix.split_long_message(long_message)
    print(f"Original length: {len(long_message)}")
    print(f"Split into {len(split_messages)} messages")
    
    # Test keyboard creation
    keyboard = UIBugFix.create_enhanced_subscription_keyboard()
    print("Keyboard created successfully")

if __name__ == '__main__':
    main() 