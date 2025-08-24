#!/usr/bin/env python3
"""
Fix Session File Naming Mismatch
Moves session files from authorization script format to scheduler format
"""

import os
import shutil

def fix_session_files():
    """Fix session file naming mismatch."""
    print("🔧 Fixing Session File Naming Mismatch")
    print("=" * 50)
    
    # Create sessions directory if it doesn't exist
    os.makedirs('sessions', exist_ok=True)
    
    # Find session files created by authorization script
    auth_session_files = []
    for i in range(1, 11):
        auth_file = f"session_worker_{i}.session"
        if os.path.exists(auth_file):
            auth_session_files.append((i, auth_file))
    
    print(f"📁 Found {len(auth_session_files)} authorization session files:")
    for worker_id, filename in auth_session_files:
        print(f"  • Worker {worker_id}: {filename}")
    
    # Move files to scheduler format
    moved_count = 0
    for worker_id, auth_file in auth_session_files:
        scheduler_file = f"sessions/worker_{worker_id}.session"
        
        try:
            # Copy file to new location
            shutil.copy2(auth_file, scheduler_file)
            print(f"✅ Moved {auth_file} → {scheduler_file}")
            moved_count += 1
        except Exception as e:
            print(f"❌ Failed to move {auth_file}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"  • Authorization files found: {len(auth_session_files)}")
    print(f"  • Files moved to scheduler format: {moved_count}")
    
    # Verify scheduler can find the files
    print(f"\n🔍 Verifying scheduler can find session files:")
    for i in range(1, 11):
        scheduler_file = f"sessions/worker_{i}.session"
        if os.path.exists(scheduler_file):
            size = os.path.getsize(scheduler_file)
            print(f"  ✅ Worker {i}: {scheduler_file} ({size} bytes)")
        else:
            print(f"  ❌ Worker {i}: {scheduler_file} (missing)")
    
    return moved_count

if __name__ == "__main__":
    fix_session_files()
