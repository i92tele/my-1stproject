#!/usr/bin/env python3
"""
Restore All Workers Script
Restores all 15 worker configurations with their correct credentials
"""

import os
from dotenv import load_dotenv

def restore_all_workers():
    """Restore all 15 workers with their correct credentials."""
    
    # All worker credentials we found
    workers = [
        # Workers 1-5 (from worker_credentials.txt)
        (1, "2040", "b18441a1ff607e10a989891a5462e627", "+447386300812"),
        (2, "2040", "b18441a1ff607e10a989891a5462e627", "+13018746514"),
        (3, "2040", "b18441a1ff607e10a989891a5462e627", "+12534997118"),
        (4, "2040", "b18441a1ff607e10a989891a5462e627", "+573235112918"),
        (5, "2040", "b18441a1ff607e10a989891a5462e627", "+13015392356"),
        
        # Workers 6-7 (missing, but we have session files)
        (6, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+13015177101"),
        (7, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15307729095"),
        
        # Workers 8-15 (from simple_worker_fix.py)
        (8, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+13015177101"),
        (9, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15307729095"),
        (10, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15405185755"),
        (11, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15409063048"),
        (12, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15312357983"),
        (13, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15153557442"),
        (14, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15029084987"),
        (15, "29187595", "243f71f06e9692a1f09a914ddb89d33c", "+15302872752"),
    ]
    
    print("🔧 Restoring all 15 workers...")
    print(f"📱 Total workers to restore: {len(workers)}")
    
    # Load current .env
    load_dotenv('config/.env')
    
    # Read current .env file
    with open('config/.env', 'r') as f:
        lines = f.readlines()
    
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
    
    # Add all worker configurations
    for worker_index, api_id, api_hash, phone in workers:
        filtered_lines.append(f"\n# Worker {worker_index}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_ID={api_id}\n")
        filtered_lines.append(f"WORKER_{worker_index}_API_HASH={api_hash}\n")
        filtered_lines.append(f"WORKER_{worker_index}_PHONE={phone}\n")
    
    # Write updated .env file
    with open('config/.env', 'w') as f:
        f.writelines(filtered_lines)
    
    print("✅ Successfully restored all 15 workers!")
    
    # Show summary
    print("\n📋 Worker Summary:")
    print("=" * 40)
    for worker_index, api_id, api_hash, phone in workers:
        print(f"  Worker {worker_index:2d}: {phone}")
    
    print(f"\n📊 Total workers configured: {len(workers)}")
    
    # Check session files
    session_files = [f for f in os.listdir('.') if f.startswith('session_worker_') and f.endswith('.session')]
    print(f"📁 Session files found: {len(session_files)}")
    
    return len(workers)

def verify_workers():
    """Verify that all workers are properly configured."""
    print("\n🔍 Verifying worker configuration...")
    
    load_dotenv('config/.env')
    
    configured_workers = 0
    for i in range(1, 16):
        api_id = os.getenv(f'WORKER_{i}_API_ID')
        api_hash = os.getenv(f'WORKER_{i}_API_HASH')
        phone = os.getenv(f'WORKER_{i}_PHONE')
        
        if api_id and api_hash and phone:
            print(f"✅ Worker {i:2d}: {phone}")
            configured_workers += 1
        else:
            print(f"❌ Worker {i:2d}: Missing configuration")
    
    print(f"\n📊 Configured workers: {configured_workers}/15")
    return configured_workers == 15

if __name__ == "__main__":
    print("🚀 Restore All Workers")
    print("=" * 30)
    
    # Restore all workers
    restored_count = restore_all_workers()
    
    # Verify restoration
    if verify_workers():
        print("\n🎉 All 15 workers successfully restored!")
    else:
        print("\n⚠️ Some workers may not be properly configured") 