#!/usr/bin/env python3
"""
AutoFarming Bot Health Monitor
Monitors bot health and performance
"""

import psutil
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_bot_process():
    """Check if bot process is running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python3' in proc.info['name'] and 'main.py' in ' '.join(proc.info['cmdline']):
                return True, proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None

def check_system_resources():
    """Check system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent
    }

def main():
    """Main monitoring function."""
    logger.info("🔍 Starting AutoFarming Bot Health Monitor...")
    
    while True:
        try:
            # Check bot process
            bot_running, pid = check_bot_process()
            
            if bot_running:
                logger.info(f"✅ Bot running (PID: {pid})")
            else:
                logger.warning("⚠️ Bot not running")
            
            # Check system resources
            resources = check_system_resources()
            logger.info(f"📊 System: CPU {resources['cpu_percent']}%, "
                       f"Memory {resources['memory_percent']}%, "
                       f"Disk {resources['disk_percent']}%")
            
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped")
            break
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
