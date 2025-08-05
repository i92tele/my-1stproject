#!/usr/bin/env python3
"""
Simple startup script for AutoFarming Pro
Usage: python3 start_bot.py
"""

import subprocess
import time
import sys

def main():
    print("🚀 AutoFarming Pro - Starting All Services")
    print("=" * 50)
    
    # Stop any existing processes
    print("🛑 Stopping existing processes...")
    subprocess.run(['pkill', '-f', 'python3 bot.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3 scheduler.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3 payment_monitor.py'], capture_output=True)
    time.sleep(2)
    
    # Start services with delays
    services = [
        ("Main Bot", "python3 bot.py"),
        ("Scheduler", "python3 scheduler.py"),
        ("Payment Monitor", "python3 payment_monitor.py")
    ]
    
    processes = []
    
    for name, command in services:
        print(f"🚀 Starting {name}...")
        process = subprocess.Popen(command.split())
        processes.append((name, process))
        print(f"✅ {name} started (PID: {process.pid})")
        time.sleep(3)  # 3 second delay
    
    print("\n🎉 All services started!")
    print("📊 Running services:")
    for name, process in processes:
        print(f"   • {name} (PID: {process.pid})")
    
    print("\n💡 Press Ctrl+C to stop all services")
    
    try:
        # Keep running and monitor
        while True:
            time.sleep(30)
            print("🔍 Checking services...")
            for name, process in processes:
                if process.poll() is None:
                    print(f"✅ {name} is running")
                else:
                    print(f"❌ {name} has stopped")
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        for name, process in processes:
            process.terminate()
            print(f"✅ Stopped {name}")
        print("✅ All services stopped")

if __name__ == "__main__":
    main() 