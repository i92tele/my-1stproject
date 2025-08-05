#!/usr/bin/env python3
"""
Final Worker Cleanup Script
Removes all frozen workers and keeps only the 2 working ones we actually have
"""

import os
from dotenv import load_dotenv

def final_cleanup():
    """Final cleanup to keep only the 2 working workers."""
    
    # Only 2 working workers we actually have
    working_workers = {
        1: "+447386300812",
        4: "+573235112918"
    }
    
    print("🗑️ Final cleanup - removing all frozen workers...")
    print("=" * 50)
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Read current .env file
    with open('config/.env', 'r') as f:
        lines = f.readlines()
    
    # Remove ALL existing worker configurations
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
    
    # Add only the 2 working workers
    for worker_index, phone in working_workers.items():
        # Use the API credentials from the backup
        if worker_index == 1:
            api_id = "2040"
            api_hash = "b18441a1ff607e10a989891a5462e627"
        else:  # worker 4
            api_id = "29187595"
            api_hash = "243f71f06e9692a1f09a914ddb89d33c"
        
        filtered_lines.append(f"\n# Worker {worker_index}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_ID={api_id}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_HASH={api_hash}\n")
        filtered_lines.append(f"WORKER_{worker_index}_PHONE={phone}\n")
    
    # Write updated .env file
    with open('config/.env', 'w') as f:
        f.writelines(filtered_lines)
    
    print(f"✅ Kept 2 working workers:")
    for worker_index, phone in working_workers.items():
        print(f"  • Worker {worker_index}: {phone}")
    
    return working_workers

def cleanup_session_files():
    """Remove all session files except the 2 working ones."""
    print("\n🗑️ Cleaning up session files...")
    
    # Keep only session files for working workers
    working_workers = [1, 4]
    
    removed_count = 0
    kept_count = 0
    
    for i in range(1, 16):
        session_file = f'session_worker_{i}.session'
        if os.path.exists(session_file):
            if i in working_workers:
                print(f"✅ Keeping {session_file}")
                kept_count += 1
            else:
                os.remove(session_file)
                print(f"🗑️ Removed {session_file}")
                removed_count += 1
    
    print(f"\n📊 Session cleanup:")
    print(f"  • Kept: {kept_count} session files")
    print(f"  • Removed: {removed_count} session files")
    
    return kept_count, removed_count

def verify_final_status():
    """Verify the final status."""
    print("\n🔍 Final verification...")
    print("=" * 30)
    
    load_dotenv('config/.env')
    
    configured_workers = []
    for i in range(1, 20):
        phone = os.getenv(f'WORKER_{i}_PHONE')
        if phone:
            configured_workers.append((i, phone))
    
    session_files = [f for f in os.listdir('.') if f.startswith('session_worker_') and f.endswith('.session')]
    
    print("📱 Configured workers:")
    for worker_index, phone in configured_workers:
        print(f"  ✅ Worker {worker_index}: {phone}")
    
    print(f"\n📄 Session files:")
    for session in sorted(session_files):
        size = os.path.getsize(session)
        print(f"  📄 {session} ({size} bytes)")
    
    print(f"\n📊 Final Status:")
    print(f"  • Configured workers: {len(configured_workers)}")
    print(f"  • Session files: {len(session_files)}")
    
    success = len(configured_workers) == 2 and len(session_files) == 2
    
    if success:
        print("\n🎉 Successfully cleaned up! Only 2 working workers remain.")
    else:
        print("\n⚠️ Cleanup may not be complete.")
    
    return success

if __name__ == "__main__":
    print("🚀 Final Worker Cleanup")
    print("=" * 30)
    
    # Final cleanup
    working_workers = final_cleanup()
    
    # Clean up session files
    kept_sessions, removed_sessions = cleanup_session_files()
    
    # Verify final status
    success = verify_final_status()
    
    if success:
        print("\n✅ Ready to start bot with 2 working workers!")
    else:
        print("\n❌ Cleanup incomplete, please check manually.") 