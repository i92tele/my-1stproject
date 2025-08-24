#!/usr/bin/env python3
"""
Emergency Bot Restart Script

This script helps restart the bot when it freezes.
"""

import os
import signal
import subprocess
import time
import psutil

def find_bot_processes():
    """Find all Python processes that might be running the bot."""
    bot_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'start_bot.py' in cmdline or 'bot.py' in cmdline:
                    bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return bot_processes

def kill_bot_processes():
    """Kill all bot processes."""
    processes = find_bot_processes()
    if not processes:
        print("✅ No bot processes found running")
        return True
    
    print(f"🔍 Found {len(processes)} bot process(es):")
    for proc in processes:
        print(f"  - PID {proc.pid}: {' '.join(proc.cmdline() or [])}")
    
    print("\n🔄 Stopping bot processes...")
    for proc in processes:
        try:
            proc.terminate()
            print(f"  - Sent terminate signal to PID {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"  - Error terminating PID {proc.pid}: {e}")
    
    # Wait for processes to terminate
    print("⏳ Waiting for processes to terminate...")
    time.sleep(3)
    
    # Force kill if still running
    for proc in processes:
        try:
            if proc.is_running():
                proc.kill()
                print(f"  - Force killed PID {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    print("✅ Bot processes stopped")
    return True

def start_bot():
    """Start the bot."""
    print("🚀 Starting bot...")
    try:
        # Start the bot in the background
        subprocess.Popen(['python3', 'start_bot.py'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        print("✅ Bot started successfully")
        return True
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return False

def main():
    """Main function."""
    print("=" * 60)
    print("🚨 EMERGENCY BOT RESTART")
    print("=" * 60)
    
    # Step 1: Kill existing processes
    print("Step 1: Stopping existing bot processes...")
    kill_bot_processes()
    
    # Step 2: Wait a moment
    print("\nStep 2: Waiting for cleanup...")
    time.sleep(2)
    
    # Step 3: Start the bot
    print("\nStep 3: Starting bot...")
    if start_bot():
        print("\n✅ Bot restart completed successfully!")
        print("\n📋 Next steps:")
        print("1. Wait 10-15 seconds for bot to fully start")
        print("2. Test /admin command")
        print("3. Test worker status button")
        print("4. Verify no more freezing")
    else:
        print("\n❌ Bot restart failed!")
        print("Please check the logs and try again manually.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
