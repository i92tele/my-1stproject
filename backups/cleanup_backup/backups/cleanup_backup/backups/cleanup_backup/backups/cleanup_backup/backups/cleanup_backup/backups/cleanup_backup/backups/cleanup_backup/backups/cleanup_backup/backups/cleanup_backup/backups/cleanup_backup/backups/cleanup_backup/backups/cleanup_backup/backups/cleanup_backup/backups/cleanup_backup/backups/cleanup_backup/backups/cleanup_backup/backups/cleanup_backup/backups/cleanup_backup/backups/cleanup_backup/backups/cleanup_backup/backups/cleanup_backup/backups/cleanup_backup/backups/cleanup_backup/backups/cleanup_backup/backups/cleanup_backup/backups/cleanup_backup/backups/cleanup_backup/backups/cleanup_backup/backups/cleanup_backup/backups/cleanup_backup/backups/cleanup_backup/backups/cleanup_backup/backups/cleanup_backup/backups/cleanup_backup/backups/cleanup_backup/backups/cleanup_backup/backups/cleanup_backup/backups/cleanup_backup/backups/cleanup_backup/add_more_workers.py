#!/usr/bin/env python3
"""
Add More Workers Script
Adds additional worker phone numbers to the existing configuration
"""

import os
from dotenv import load_dotenv

def add_more_workers():
    """Add more worker phone numbers to the configuration."""
    
    # Additional worker phone numbers (add your new numbers here)
    additional_workers = [
        # Add your additional phone numbers here
        # Example: "+1234567890",
        # Example: "+9876543210",
    ]
    
    # Test API credentials (same as existing workers)
    api_id = "2040"
    api_hash = "b18441a1ff607e10a989891a5462e627"
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Find the next available worker number
    next_worker = 1
    while os.getenv(f'WORKER_{next_worker}_PHONE'):
        next_worker += 1
    
    print(f"📱 Current workers: {next_worker - 1}")
    print(f"🔢 Next worker number: {next_worker}")
    
    # Get additional phone numbers from user
    print("\n📞 Enter additional phone numbers (one per line, press Enter twice when done):")
    print("Format: +1234567890 (with country code)")
    
    new_workers = []
    while True:
        phone = input(f"Phone number for Worker {next_worker + len(new_workers)} (or press Enter to finish): ").strip()
        if not phone:
            break
        new_workers.append(phone)
    
    if not new_workers:
        print("❌ No additional workers added")
        return
    
    # Add to .env file
    worker_config = "\n# Additional Worker Credentials\n"
    
    for i, phone in enumerate(new_workers):
        worker_num = next_worker + i
        worker_config += f"\n# Worker {worker_num}\n"
        worker_config += f"WORKER_{worker_num}_API_ID={api_id}\n"
        worker_config += f"WORKER_{worker_num}_API_HASH={api_hash}\n"
        worker_config += f"WORKER_{worker_num}_PHONE={phone}\n"
    
    # Append to .env file
    with open('config/.env', 'a') as f:
        f.write(worker_config)
    
    print(f"\n✅ Added {len(new_workers)} more workers!")
    print(f"📱 New workers: {', '.join(new_workers)}")
    print(f"📊 Total workers now: {next_worker - 1 + len(new_workers)}")
    
    return len(new_workers)

def show_current_workers():
    """Show all currently configured workers."""
    print("\n📋 Current Worker Configuration:")
    print("=" * 40)
    
    load_dotenv('config/.env')
    
    workers = []
    for i in range(1, 50):  # Check up to 50 workers
        phone = os.getenv(f'WORKER_{i}_PHONE')
        if phone:
            workers.append((i, phone))
    
    if workers:
        for worker_num, phone in workers:
            print(f"  Worker {worker_num}: {phone}")
    else:
        print("  No workers configured")
    
    print(f"\n📊 Total workers: {len(workers)}")

if __name__ == "__main__":
    print("🚀 Add More Workers")
    print("=" * 30)
    
    # Show current workers
    show_current_workers()
    
    # Add more workers
    new_count = add_more_workers()
    
    if new_count > 0:
        print(f"\n✅ Successfully added {new_count} more workers!")
        print("\n📝 Next steps:")
        print("1. Run: python3 test_workers_simple.py")
        print("2. Update scheduler.py for multi-worker support")
        print("3. Test all workers with verification codes")
    else:
        print("\n❌ No new workers were added") 