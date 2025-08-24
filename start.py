#!/usr/bin/env python3
"""
Simple Bot Startup Script
One script to start everything
"""

import subprocess
import time
import os

def start_bot():
    """Start the bot system."""
    print("🚀 Starting AutoFarming Bot...")
    print("=" * 40)
    
    # Kill any existing processes
    print("🛑 Stopping old processes...")
    subprocess.run(['pkill', '-f', 'python3 bot.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3 -m scheduler'], capture_output=True)
    subprocess.run(['pkill', '-f', 'python3 payment_monitor.py'], capture_output=True)
    time.sleep(2)
    
    # Start main bot
    print("🤖 Starting main bot...")
    bot_process = subprocess.Popen(
        ["python3", "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"✅ Bot started (PID: {bot_process.pid})")
    
    # Wait for bot to initialize
    print("⏳ Waiting 10 seconds...")
    time.sleep(10)
    
    # Start scheduler
    print("📅 Starting scheduler...")
    scheduler_process = subprocess.Popen(
        ["python3", "-m", "scheduler"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"✅ Scheduler started (PID: {scheduler_process.pid})")
    
    # Start payment monitor if exists
    if os.path.exists("payment_monitor.py"):
        print("💰 Starting payment monitor...")
        payment_process = subprocess.Popen(
            ["python3", "payment_monitor.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✅ Payment monitor started (PID: {payment_process.pid})")
    
    print("\n🎉 Bot system is running!")
    print("📱 Test with /start in Telegram")
    print("💡 Press Ctrl+C to stop")

if __name__ == "__main__":
    start_bot()
