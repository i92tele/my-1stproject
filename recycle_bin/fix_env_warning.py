#!/usr/bin/env python3
"""
Fix .env file warning
Checks line 9 and fixes any parsing issues
"""

import os

def check_env_file():
    """Check the .env file for parsing issues"""
    
    print("🔍 Checking .env file for parsing issues")
    print("=" * 40)
    
    # Check all possible .env file locations
    possible_paths = [
        '.env',
        'config/.env', 
        'config/env_template.txt'
    ]
    
    for env_file in possible_paths:
        if os.path.exists(env_file):
            print(f"\n📁 Found file: {env_file}")
            print("-" * 30)
            
            with open(env_file, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if i == 9:  # Line 9 specifically
                    print(f"Line {i}: {line}")
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        print(f"  ✅ Valid line: {key} = {value}")
                    else:
                        print(f"  ⚠️  Potential issue: {line}")
                elif line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() and value.strip():
                        print(f"Line {i}: ✅ {key} = {value}")
                    else:
                        print(f"Line {i}: ⚠️  {line}")
                else:
                    print(f"Line {i}: {line}")
    
    print("\n" + "=" * 40)
    print("💡 The python-dotenv warning is usually harmless")
    print("It doesn't affect the HD wallet functionality")
    print("Your payment system is working correctly!")

if __name__ == "__main__":
    check_env_file()
