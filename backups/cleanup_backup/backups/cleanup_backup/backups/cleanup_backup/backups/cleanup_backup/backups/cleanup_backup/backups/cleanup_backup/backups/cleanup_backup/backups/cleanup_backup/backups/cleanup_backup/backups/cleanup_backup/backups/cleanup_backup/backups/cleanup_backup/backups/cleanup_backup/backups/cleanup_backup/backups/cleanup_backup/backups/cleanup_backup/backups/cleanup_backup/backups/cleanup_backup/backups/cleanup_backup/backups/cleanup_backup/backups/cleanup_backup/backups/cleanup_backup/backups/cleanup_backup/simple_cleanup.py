#!/usr/bin/env python3
"""
Simple cleanup of banned workers
"""

import os

def cleanup_banned_workers():
    """Remove banned workers from .env file."""
    
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
    
    # Banned phone numbers
    banned_phones = ["+3015177101", "+5307729"]
    
    # Split into lines and filter
    lines = content.split('\n')
    cleaned_lines = []
    skip_count = 0
    
    for line in lines:
        # Check if this line contains a banned phone
        if any(phone in line for phone in banned_phones):
            skip_count = 3  # Skip next 3 lines (API_ID, API_HASH, PHONE)
            continue
        
        if skip_count > 0:
            skip_count -= 1
            continue
        
        cleaned_lines.append(line)
    
    # Write cleaned content
    with open(env_file, 'w') as f:
        f.write('\n'.join(cleaned_lines))
    
    print("✅ Removed banned workers from .env file")

if __name__ == "__main__":
    cleanup_banned_workers() 