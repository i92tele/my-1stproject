#!/usr/bin/env python3
"""
Fix Subscription Menu Back Button
Replaces "❓ Help" with "🔙 Back to Menu" in subscription menus
"""

import re

def fix_subscription_menu():
    """Fix the subscription menu back button."""
    
    # Read the file
    with open('commands/user_commands.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the help button with back button in subscription menus
    # Look for the specific pattern in subscription context
    old_pattern = 'InlineKeyboardButton("❓ Help", callback_data="help")'
    new_pattern = 'InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd:start")'
    
    # Apply the replacement
    new_content = content.replace(old_pattern, new_pattern)
    
    # Write back to file
    with open('commands/user_commands.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Fixed subscription menu back button")

if __name__ == "__main__":
    fix_subscription_menu()
