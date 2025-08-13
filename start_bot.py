#!/usr/bin/env python3
"""
AutoFarming Bot - Enhanced Startup Script
Supports both legacy and new organized structure
Usage: python3 start_bot.py [--new] [--legacy] [--scheduler-only] [--bot-only]
"""

import subprocess
import time
import sys
import os
import argparse
from pathlib import Path

def check_health():
    """Quick health check before starting services."""
    print("🔍 Running health check...")
    try:
        result = subprocess.run(['python3', 'health_check.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Health check passed")
            return True
        else:
            print("⚠️ Health check warnings (continuing anyway)")
            return True
    except Exception as e:
        print(f"⚠️ Health check failed: {e} (continuing anyway)")
        return True

def stop_existing_processes():
    """Stop any existing bot processes."""
    print("🛑 Stopping existing processes...")
    processes_to_stop = [
        'python3 bot.py',
        'python3 scheduler.py', 
        'python3 payment_monitor.py',
        'python3 -m scheduler'
    ]
    
    for process in processes_to_stop:
        subprocess.run(['pkill', '-f', process], capture_output=True)
    
    time.sleep(2)
    print("✅ Stopped existing processes")

def start_legacy_services():
    """Start services using legacy structure."""
    print("📁 Using LEGACY structure")
    print("⚠️ Note: Using delays to prevent database conflicts")
    
    services = [
        ("Main Bot", "python3 bot.py"),
        ("Payment Monitor", "python3 payment_monitor.py")
    ]
    
    # Check if scheduler.py exists for legacy
    if os.path.exists("scheduler.py"):
        services.append(("Legacy Scheduler", "python3 scheduler.py"))
    else:
        services.append(("New Scheduler", "python3 -m scheduler"))
    
    return start_services_with_delays(services)

def start_new_services():
    """Start services using new organized structure."""
    print("📁 Using NEW organized structure")
    print("⚠️ Note: Using delays to prevent database conflicts")
    
    # Set environment variable to disable internal posting service
    os.environ['DISABLE_INTERNAL_POSTING_SERVICE'] = '1'
    print("🔧 Set DISABLE_INTERNAL_POSTING_SERVICE=1 to prevent conflicts")
    
    # Start services with longer delays to prevent database locks
    services = [
        ("Main Bot", "python3 bot.py"),
        ("New Scheduler", "python3 -m scheduler")
    ]
    
    # Add payment monitor if it exists
    if os.path.exists("payment_monitor.py"):
        services.append(("Payment Monitor", "python3 payment_monitor.py"))
    else:
        print("⚠️ payment_monitor.py not found - skipping payment monitor")
    
    return start_services_with_delays(services)

def start_scheduler_only():
    """Start only the scheduler service."""
    print("📅 Starting SCHEDULER only")
    services = [("Scheduler", "python3 -m scheduler")]
    return start_services(services)

def start_bot_only():
    """Start only the bot service."""
    print("🤖 Starting BOT only")
    services = [("Main Bot", "python3 bot.py")]
    return start_services(services)

def start_services(services):
    """Start the specified services."""
    processes = []
    
    for name, command in services:
        print(f"🚀 Starting {name}...")
        try:
            # Pass current environment to subprocess and activate venv
            env = os.environ.copy()
            
            # Activate virtual environment if it exists
            venv_path = Path("venv/bin/activate")
            if venv_path.exists():
                # Use bash to source venv and run command
                bash_command = f"source venv/bin/activate && {command}"
                process = subprocess.Popen(bash_command, shell=True, env=env, executable='/bin/bash')
            else:
                process = subprocess.Popen(command.split(), env=env)
            processes.append((name, process))
            print(f"✅ {name} started (PID: {process.pid})")
            time.sleep(3)  # 3 second delay between services
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
    
    return processes

def start_services_with_delays(services):
    """Start services with extended delays to prevent database conflicts."""
    processes = []
    
    for i, (name, command) in enumerate(services):
        print(f"🚀 Starting {name}...")
        try:
            # Pass current environment to subprocess and activate venv
            env = os.environ.copy()
            
            # Activate virtual environment if it exists
            venv_path = Path("venv/bin/activate")
            if venv_path.exists():
                # Use bash to source venv and run command
                bash_command = f"source venv/bin/activate && {command}"
                process = subprocess.Popen(bash_command, shell=True, env=env, executable='/bin/bash')
            else:
                process = subprocess.Popen(command.split(), env=env)
            processes.append((name, process))
            print(f"✅ {name} started (PID: {process.pid})")
            
            # Progressive delays: first service 5s, second 10s, third 15s
            if i < len(services) - 1:  # Don't delay after last service
                delay = 5 + (i * 5)  # 5, 10, 15 seconds
                print(f"⏳ Waiting {delay} seconds for {name} to initialize before starting next service...")
                
                # Show countdown
                for remaining in range(delay, 0, -1):
                    print(f"   ⏱️  {remaining} seconds remaining...", end='\r')
                    time.sleep(1)
                print("   ✅ Ready for next service" + " " * 20)  # Clear countdown line
                
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
    
    return processes

def monitor_services(processes):
    """Monitor running services."""
    print("\n🎉 All services started!")
    print("📊 Running services:")
    for name, process in processes:
        print(f"   • {name} (PID: {process.pid})")
    
    print("\n💡 Press Ctrl+C to stop all services")
    print("📋 Service status will be checked every 30 seconds")
    
    try:
        while True:
            time.sleep(30)
            print(f"\n🔍 [{time.strftime('%H:%M:%S')}] Checking services...")
            
            alive_count = 0
            for name, process in processes:
                if process.poll() is None:
                    print(f"✅ {name} is running (PID: {process.pid})")
                    alive_count += 1
                else:
                    print(f"❌ {name} has stopped (exit code: {process.returncode})")
            
            print(f"📊 Status: {alive_count}/{len(processes)} services running")
            
            if alive_count == 0:
                print("⚠️ All services have stopped!")
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 [{time.strftime('%H:%M:%S')}] Stopping all services...")
        for name, process in processes:
            try:
                process.terminate()
                print(f"✅ Stopped {name}")
            except:
                print(f"⚠️ {name} already stopped")
        print("✅ All services stopped")

def main():
    parser = argparse.ArgumentParser(description='AutoFarming Bot Startup Script')
    parser.add_argument('--new', action='store_true', help='Use new organized structure')
    parser.add_argument('--legacy', action='store_true', help='Use legacy structure')
    parser.add_argument('--scheduler-only', action='store_true', help='Start only scheduler')
    parser.add_argument('--bot-only', action='store_true', help='Start only bot')
    parser.add_argument('--no-health-check', action='store_true', help='Skip health check')
    
    args = parser.parse_args()
    
    print("🚀 AutoFarming Bot - Enhanced Startup Script")
    print("=" * 55)
    print(f"📂 Working Directory: {os.getcwd()}")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    
    # Health check
    if not args.no_health_check:
        if not check_health():
            print("❌ Health check failed. Use --no-health-check to skip.")
            return 1
    
    # Stop existing processes
    stop_existing_processes()
    
    # Determine which services to start
    if args.scheduler_only:
        processes = start_scheduler_only()
    elif args.bot_only:
        processes = start_bot_only()
    elif args.new:
        processes = start_new_services()
    elif args.legacy:
        processes = start_legacy_services()
    else:
        # Auto-detect best structure
        if os.path.exists("src/") and os.path.exists("scheduler/"):
            print("🔍 Auto-detected: NEW organized structure available")
            processes = start_new_services()
        else:
            print("🔍 Auto-detected: Using LEGACY structure")
            processes = start_legacy_services()
    
    if not processes:
        print("❌ No services started!")
        return 1
    
    # Monitor services
    monitor_services(processes)
    return 0

if __name__ == "__main__":
    main() 