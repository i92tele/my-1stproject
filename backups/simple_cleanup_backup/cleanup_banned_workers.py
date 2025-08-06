#!/usr/bin/env python3
"""
Cleanup Banned Workers
Removes banned workers from the configuration
"""

import os
from dotenv import load_dotenv

def cleanup_banned_workers():
    """Remove banned workers from .env file."""
    
    # Banned phone numbers to remove
    banned_phones = [
        "+3015177101",  # Worker 6
        "+5307729"      # Worker 7
    ]
    
    print("🧹 Cleaning up banned workers...")
    print(f"❌ Removing: {', '.join(banned_phones)}")
    
    # Read current .env file
    try:
        with open('config/.env', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("❌ .env file not found")
        return
    
    # Filter out banned workers
    cleaned_lines = []
    skip_next_lines = 0
    removed_count = 0
    
    for line in lines:
        # Check if this line contains a banned phone
        if any(phone in line for phone in banned_phones):
            skip_next_lines = 3  # Skip API_ID, API_HASH, and PHONE lines
            removed_count += 1
            continue
        
        # Skip lines if we're in a banned worker block
        if skip_next_lines > 0:
            skip_next_lines -= 1
            continue
        
        cleaned_lines.append(line)
    
    # Write cleaned .env file
    with open('config/.env', 'w') as f:
        f.writelines(cleaned_lines)
    
    print(f"✅ Removed {removed_count} banned workers")
    print("📝 .env file updated")

def renumber_workers():
    """Renumber workers to fill gaps."""
    print("\n🔢 Renumbering workers...")
    
    # Read current .env file
    try:
        with open('config/.env', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ .env file not found")
        return
    
    # Find all worker configurations
    import re
    
    # Pattern to match worker configurations
    pattern = r'# Worker (\d+)\nWORKER_\d+_API_ID=(\d+)\nWORKER_\d+_API_HASH=([^\n]+)\nWORKER_\d+_PHONE=([^\n]+)'
    
    matches = re.findall(pattern, content)
    
    if not matches:
        print("❌ No worker configurations found")
        return
    
    # Create new content with renumbered workers
    new_content = content
    
    for i, (old_num, api_id, api_hash, phone) in enumerate(matches, 1):
        # Replace old worker number with new number
        old_pattern = f'# Worker {old_num}\nWORKER_{old_num}_API_ID={api_id}\nWORKER_{old_num}_API_HASH={api_hash}\nWORKER_{old_num}_PHONE={phone}'
        new_pattern = f'# Worker {i}\nWORKER_{i}_API_ID={api_id}\nWORKER_{i}_API_HASH={api_hash}\nWORKER_{i}_PHONE={phone}'
        
        new_content = new_content.replace(old_pattern, new_pattern)
    
    # Write updated .env file
    with open('config/.env', 'w') as f:
        f.write(new_content)
    
    print(f"✅ Renumbered {len(matches)} workers")

def verify_cleanup():
    """Verify the cleanup was successful."""
    print("\n🧪 Verifying cleanup...")
    
    load_dotenv('config/.env')
    
    workers = []
    for i in range(1, 50):
        phone = os.getenv(f'WORKER_{i}_PHONE')
        if phone:
            workers.append((i, phone))
    
    print(f"📊 Total workers after cleanup: {len(workers)}")
    
    if workers:
        print("\n📋 Active Workers:")
        for worker_num, phone in workers:
            print(f"  Worker {worker_num}: {phone}")
    
    # Check for banned numbers
    banned_phones = ["+3015177101", "+5307729"]
    found_banned = [phone for _, phone in workers if phone in banned_phones]
    
    if found_banned:
        print(f"❌ Still found banned numbers: {found_banned}")
    else:
        print("✅ All banned numbers removed successfully")

if __name__ == "__main__":
    print("🧹 Worker Cleanup")
    print("=" * 30)
    
    # Remove banned workers
    cleanup_banned_workers()
    
    # Renumber workers
    renumber_workers()
    
    # Verify cleanup
    verify_cleanup()
    
    print("\n✅ Cleanup complete!") 