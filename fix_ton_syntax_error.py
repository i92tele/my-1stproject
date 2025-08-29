#!/usr/bin/env python3
"""
Fix TON Payment Syntax Error
"""

import re

def fix_syntax_error():
    """Fix the syntax error in multi_crypto_payments.py."""
    
    try:
        with open('multi_crypto_payments.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the syntax error at line 1310
        # The issue is: "return False async def _verify_ton_api"
        # Should be: "return False\n\n    async def _verify_ton_api"
        
        # Find and fix the broken line
        pattern = r'return False async def _verify_ton_api'
        replacement = 'return False\n\n    async def _verify_ton_api'
        
        if pattern in content:
            content = content.replace(pattern, replacement)
            print("✅ Fixed syntax error at line 1310")
        else:
            print("⚠️ Syntax error pattern not found, checking for other issues...")
            
            # Look for other potential syntax issues
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'return False' in line and 'async def' in line:
                    print(f"❌ Found syntax error at line {i}: {line}")
                    # Fix this line
                    fixed_line = line.replace('return False', 'return False\n\n    ')
                    content = content.replace(line, fixed_line)
                    print(f"✅ Fixed line {i}")
        
        # Write the fixed content back
        with open('multi_crypto_payments.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Syntax error fixed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix syntax error: {e}")
        return False

def verify_syntax():
    """Verify that the syntax is now correct."""
    try:
        import ast
        with open('multi_crypto_payments.py', 'r', encoding='utf-8') as f:
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
    print("🔧 FIXING TON PAYMENT SYNTAX ERROR")
    print("=" * 50)
    
    if fix_syntax_error():
        if verify_syntax():
            print("✅ Syntax error fixed and verified")
        else:
            print("❌ Syntax error still exists")
    else:
        print("❌ Failed to fix syntax error")
