#!/usr/bin/env python3
"""
Fix All TON Payment Syntax Errors
"""

import re

def fix_all_syntax_errors():
    """Fix all syntax errors in multi_crypto_payments.py."""
    
    try:
        with open('multi_crypto_payments.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 Scanning for syntax errors...")
        
        # Find all instances of "return False async def"
        pattern = r'return False async def'
        matches = list(re.finditer(pattern, content))
        
        if matches:
            print(f"Found {len(matches)} syntax errors:")
            for i, match in enumerate(matches, 1):
                line_num = content[:match.start()].count('\n') + 1
                print(f"  {i}. Line {line_num}: {match.group()}")
            
            # Fix all instances
            content = re.sub(pattern, 'return False\n\n    async def', content)
            print(f"✅ Fixed {len(matches)} syntax errors")
        else:
            print("✅ No syntax errors found")
        
        # Also check for any other potential issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'return False' in line and 'async def' in line:
                print(f"⚠️ Found potential issue at line {i}: {line}")
        
        # Write the fixed content back
        with open('multi_crypto_payments.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ All syntax errors fixed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix syntax errors: {e}")
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
        # Try to find the exact line
        try:
            lines = content.split('\n')
            line_num = e.lineno
            print(f"❌ Error at line {line_num}: {lines[line_num-1]}")
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def check_method_boundaries():
    """Check that all method boundaries are correct."""
    try:
        with open('multi_crypto_payments.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all async def methods
        method_pattern = r'async def (\w+)'
        methods = re.findall(method_pattern, content)
        
        print(f"📋 Found {len(methods)} async methods:")
        for i, method in enumerate(methods[:10], 1):  # Show first 10
            print(f"  {i}. {method}")
        
        if len(methods) > 10:
            print(f"  ... and {len(methods) - 10} more")
        
        # Check for proper indentation
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('async def'):
                if not line.startswith('    async def'):
                    print(f"⚠️ Method at line {i} may have indentation issues: {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Method boundary check failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 FIXING ALL TON PAYMENT SYNTAX ERRORS")
    print("=" * 60)
    
    if fix_all_syntax_errors():
        if verify_syntax():
            print("✅ All syntax errors fixed and verified")
            check_method_boundaries()
        else:
            print("❌ Syntax errors still exist")
    else:
        print("❌ Failed to fix syntax errors")
