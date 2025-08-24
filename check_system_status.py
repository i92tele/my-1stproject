#!/usr/bin/env python3
"""
Check System Status - See what's running and what's not
"""

import subprocess
import os
import psutil
import time

def check_system_status():
    """Check the current status of all bot processes."""
    print("🔍 Checking System Status...")
    print("=" * 50)
    
    # Check for running Python processes
    print("\n🐍 Python Processes:")
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python3' or proc.info['name'] == 'python':
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if any(keyword in cmdline for keyword in ['bot.py', 'scheduler', 'payment_monitor']):
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline,
                        'status': proc.status()
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if python_processes:
        for proc in python_processes:
            print(f"  PID {proc['pid']}: {proc['cmdline']}")
            print(f"    Status: {proc['status']}")
    else:
        print("  ❌ No bot processes found")
    
    # Check for specific processes
    print("\n🎯 Specific Process Check:")
    
    processes_to_check = [
        ('Main Bot', 'python3 bot.py'),
        ('Scheduler', 'python3 -m scheduler'),
        ('Payment Monitor', 'python3 payment_monitor.py')
    ]
    
    for name, cmd in processes_to_check:
        result = subprocess.run(['pgrep', '-f', cmd], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"  ✅ {name}: Running (PIDs: {', '.join(pids)})")
        else:
            print(f"  ❌ {name}: Not running")
    
    # Check system resources
    print("\n💻 System Resources:")
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    print(f"  CPU Usage: {cpu_percent}%")
    print(f"  Memory Usage: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")
    print(f"  Disk Usage: {disk.percent}% ({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)")
    
    # Check for log files
    print("\n📋 Log Files:")
    log_files = ['logs/bot.log', 'scheduler.log', 'payment_monitor.log']
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            mtime = time.ctime(os.path.getmtime(log_file))
            print(f"  ✅ {log_file}: {size} bytes, modified {mtime}")
        else:
            print(f"  ❌ {log_file}: Not found")
    
    # Check database
    print("\n🗄️ Database:")
    if os.path.exists('bot_database.db'):
        size = os.path.getsize('bot_database.db')
        mtime = time.ctime(os.path.getmtime('bot_database.db'))
        print(f"  ✅ bot_database.db: {size} bytes, modified {mtime}")
    else:
        print("  ❌ bot_database.db: Not found")
    
    # Check environment
    print("\n🔧 Environment:")
    if os.path.exists('config/.env'):
        print("  ✅ config/.env: Found")
    else:
        print("  ❌ config/.env: Not found")
    
    if os.path.exists('venv'):
        print("  ✅ venv: Found")
    else:
        print("  ❌ venv: Not found")

if __name__ == '__main__':
    check_system_status()
