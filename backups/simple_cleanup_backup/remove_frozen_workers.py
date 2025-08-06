#!/usr/bin/env python3
"""
Remove Frozen Workers Script
Removes all frozen workers and keeps only the 3 working ones
"""

import os
from dotenv import load_dotenv

def remove_frozen_workers():
    """Remove frozen workers and keep only the 3 working ones."""
    
    # Working workers (keep these)
    working_phones = [
        "+447386300812",  # Worker 1
        "+15512984981",   # Worker 2  
        "+573235112918"   # Worker 4
    ]
    
    print("🗑️ Removing frozen workers...")
    print("=" * 40)
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Read current .env file
    with open('config/.env', 'r') as f:
        lines = f.readlines()
    
    # Find which workers to keep
    workers_to_keep = []
    for i in range(1, 16):
        phone = os.getenv(f'WORKER_{i}_PHONE')
        if phone in working_phones:
            workers_to_keep.append(i)
            print(f"✅ Keeping Worker {i}: {phone}")
    
    print(f"\n📱 Working workers to keep: {workers_to_keep}")
    
    # Remove existing worker configurations
    filtered_lines = []
    skip_worker_lines = False
    for line in lines:
        if line.startswith('# Worker') or line.startswith('WORKER_'):
            if not skip_worker_lines:
                skip_worker_lines = True
            continue
        else:
            skip_worker_lines = False
            filtered_lines.append(line)
    
    # Add only the working workers
    for worker_index in workers_to_keep:
        api_id = os.getenv(f'WORKER_{worker_index}_API_ID')
        api_hash = os.getenv(f'WORKER_{worker_index}_API_HASH')
        phone = os.getenv(f'WORKER_{worker_index}_PHONE')
        
        filtered_lines.append(f"\n# Worker {worker_index}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_ID={api_id}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_HASH={api_hash}\n")
        filtered_lines.append(f"WORKER_{worker_index}_PHONE={phone}\n")
    
    # Write updated .env file
    with open('config/.env', 'w') as f:
        f.writelines(filtered_lines)
    
    print(f"\n✅ Successfully removed frozen workers!")
    print(f"📊 Kept {len(workers_to_keep)} working workers")
    
    return workers_to_keep

def remove_frozen_session_files():
    """Remove session files for frozen workers."""
    print("\n🗑️ Removing session files for frozen workers...")
    
    # Keep session files for working workers only
    working_workers = [1, 2, 4]  # Based on the working phones
    
    removed_count = 0
    for i in range(1, 16):
        session_file = f'session_worker_{i}.session'
        if os.path.exists(session_file):
            if i in working_workers:
                print(f"✅ Keeping {session_file}")
            else:
                os.remove(session_file)
                print(f"🗑️ Removed {session_file}")
                removed_count += 1
    
    print(f"\n📊 Removed {removed_count} frozen worker session files")
    return removed_count

def verify_cleanup():
    """Verify the cleanup was successful."""
    print("\n🔍 Verifying cleanup...")
    print("=" * 30)
    
    load_dotenv('config/.env')
    
    configured_workers = 0
    for i in range(1, 20):
        phone = os.getenv(f'WORKER_{i}_PHONE')
        if phone:
            configured_workers += 1
            print(f"✅ Worker {i}: {phone}")
    
    session_files = [f for f in os.listdir('.') if f.startswith('session_worker_') and f.endswith('.session')]
    
    print(f"\n📊 Final Status:")
    print(f"  • Configured workers: {configured_workers}")
    print(f"  • Session files: {len(session_files)}")
    
    return configured_workers == 3 and len(session_files) == 3

if __name__ == "__main__":
    print("🚀 Remove Frozen Workers")
    print("=" * 30)
    
    # Remove frozen workers from .env
    kept_workers = remove_frozen_workers()
    
    # Remove frozen session files
    removed_sessions = remove_frozen_session_files()
    
    # Verify cleanup
    if verify_cleanup():
        print("\n🎉 Successfully cleaned up frozen workers!")
        print("✅ Only 3 working workers remain")
    else:
        print("\n⚠️ Cleanup may not be complete") 