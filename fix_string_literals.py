#!/usr/bin/env python3
"""
Fix Unterminated String Literals
"""

import re

def fix_string_literals():
    """Fix the unterminated string literals in user_commands.py."""
    
    try:
        with open('commands/user_commands.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 Scanning for unterminated string literals...")
        
        # Fix the specific string literal issues
        # Replace malformed multi-line strings with proper ones
        
        # Fix the first string literal
        content = re.sub(
            r'text = \(\s*"✅ Payment Completed!\s*\n\s*"\s*\n\s*f"Your subscription has been activated.\s*\n\s*"\s*\n\s*f"Payment ID: \{payment_id\}\s*\n\s*"\s*\n\s*"You can now use your ad slots."\s*\)',
            '''text = (
                "✅ Payment Completed!\\n\\n"
                f"Your subscription has been activated.\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "You can now use your ad slots."
            )''',
            content
        )
        
        # Fix the second string literal
        content = re.sub(
            r'text = \(\s*"🎉 Payment Verified!\s*\n\s*"\s*\n\s*f"✅ Subscription activated successfully!\s*\n\s*"\s*\n\s*f"🆔 Payment ID: \{payment_id\}\s*\n\s*"\s*\n\s*"You can now use your ad slots!"\s*\)',
            '''text = (
                "🎉 Payment Verified!\\n\\n"
                f"✅ Subscription activated successfully!\\n"
                f"🆔 Payment ID: {payment_id}\\n\\n"
                "You can now use your ad slots!"
            )''',
            content
        )
        
        # Fix the third string literal
        content = re.sub(
            r'text = \(\s*"⏳ Payment Pending\s*\n\s*"\s*\n\s*f"We\'re still waiting for your payment.\s*\n\s*"\s*\n\s*f"Payment ID: \{payment_id\}\s*\n\s*"\s*\n\s*f"Last checked: \{check_time\}\s*\n\s*"\s*\n\s*"Please ensure you sent the correct amount.\s*\n\s*"\s*\n\s*"Click \'Check Again\' in 30 seconds."\s*\)',
            '''text = (
                "⏳ Payment Pending\\n\\n"
                f"We're still waiting for your payment.\\n"
                f"Payment ID: {payment_id}\\n"
                f"Last checked: {check_time}\\n\\n"
                "Please ensure you sent the correct amount.\\n"
                "Click 'Check Again' in 30 seconds."
            )''',
            content
        )
        
        # Fix the fourth string literal
        content = re.sub(
            r'text = \(\s*"⏰ Payment Expired\s*\n\s*"\s*\n\s*f"Payment ID: \{payment_id\}\s*\n\s*"\s*\n\s*"Please create a new payment request."\s*\)',
            '''text = (
                "⏰ Payment Expired\\n\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "Please create a new payment request."
            )''',
            content
        )
        
        # Fix the fifth string literal
        content = re.sub(
            r'text = \(\s*f"❓ Payment Status: \{status\[\'status\'\]\}\s*\n\s*"\s*\n\s*f"Payment ID: \{payment_id\}\s*\n\s*"\s*\n\s*"Please contact support for assistance."\s*\)',
            '''text = (
                f"❓ Payment Status: {status['status']}\\n\\n"
                f"Payment ID: {payment_id}\\n\\n"
                "Please contact support for assistance."
            )''',
            content
        )
        
        # Write the fixed content back
        with open('commands/user_commands.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ String literals fixed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix string literals: {e}")
        return False

def verify_syntax():
    """Verify that the syntax is now correct."""
    try:
        import ast
        with open('commands/user_commands.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the file
        ast.parse(content)
        print("✅ Syntax verification passed")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error still exists: {e}")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 FIXING UNTERMINATED STRING LITERALS")
    print("=" * 50)
    
    if fix_string_literals():
        if verify_syntax():
            print("✅ String literals fixed and syntax verified")
        else:
            print("❌ Syntax error still exists")
    else:
        print("❌ Failed to fix string literals")
