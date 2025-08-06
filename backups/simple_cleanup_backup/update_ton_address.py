#!/usr/bin/env python3
"""
Update TON Address
Updates the TON address in .env file with a valid address
"""

import os
import re

def update_ton_address():
    """Update TON address in .env file."""
    
    # Your valid TON address
    new_ton_address = "UQAF5N1Eke85knjNZNXz6tIwuiTb_GL6CpIHwT6ifWdcN_Y6"
    
    print(f"🔧 Updating TON address to: {new_ton_address}")
    
    # Find .env file
    env_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == '.env':
                env_files.append(os.path.join(root, file))
    
    if not env_files:
        print("❌ No .env file found")
        return
    
    env_file = env_files[0]
    print(f"📁 Found .env file: {env_file}")
    
    # Read current content
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Update TON_ADDRESS
    if 'TON_ADDRESS=' in content:
        # Replace existing TON_ADDRESS
        content = re.sub(r'TON_ADDRESS=.*', f'TON_ADDRESS={new_ton_address}', content)
        print("✅ Updated existing TON_ADDRESS")
    else:
        # Add TON_ADDRESS if it doesn't exist
        content += f'\nTON_ADDRESS={new_ton_address}'
        print("✅ Added new TON_ADDRESS")
    
    # Write updated content
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ TON address updated successfully!")
    
    # Verify the update
    with open(env_file, 'r') as f:
        updated_content = f.read()
        if new_ton_address in updated_content:
            print("✅ Verification: TON address found in .env file")
        else:
            print("❌ Verification failed: TON address not found")

if __name__ == "__main__":
    update_ton_address() 