#!/usr/bin/env python3
"""Check syntax errors in user_commands.py"""

import ast
import sys

def check_syntax(filename):
    """Check if a Python file has syntax errors."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Try to parse the AST
        ast.parse(source)
        print(f"✅ {filename} has no syntax errors")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in {filename}:")
        print(f"   Line {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return False

if __name__ == "__main__":
    success = check_syntax("commands/user_commands.py")
    sys.exit(0 if success else 1)
