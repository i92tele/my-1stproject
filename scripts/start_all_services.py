#!/usr/bin/env python3
"""
AutoFarming Pro - Unified Service Startup Script
Launches all services with proper delays to prevent system overload
"""

import subprocess
import time
import os
import sys
import signal
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.delay_between_services = 3  # 3 second delay
        
    def start_service(self, name: str, command: str, description: str):
        """Start a service with logging."""
        try:
            logger.info(f"🚀 Starting {name}: {description}")
            
            # Start the process
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            self.processes[name] = process
            logger.info(f"✅ {name} started (PID: {process.pid})")
            
            # Wait before starting next service
            time.sleep(self.delay_between_services)
            
        except Exception as e:
            logger.error(f"❌ Failed to start {name}: {e}")
    
    def stop_all_services(self):
        """Stop all running services."""
        logger.info("🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            try:
                # Kill the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                logger.info(f"✅ Stopped {name}")
            except Exception as e:
                logger.error(f"❌ Error stopping {name}: {e}")
        
        self.processes.clear()
    
    def check_services(self):
        """Check if all services are running."""
        logger.info("🔍 Checking service status...")
        
        for name, process in self.processes.items():
            if process.poll() is None:
                logger.info(f"✅ {name} is running (PID: {process.pid})")
            else:
                logger.error(f"❌ {name} has stopped")
    
    def start_all_services(self):
        """Start all services in the correct order."""
        logger.info("🎯 AutoFarming Pro - Starting All Services")
        logger.info("=" * 50)
        
        # 1. Check if bot is already running
        try:
            result = subprocess.run(['pgrep', '-f', 'python3 bot.py'], capture_output=True)
            if result.returncode == 0:
                logger.warning("⚠️ Bot is already running. Stopping existing processes...")
                subprocess.run(['pkill', '-f', 'python3 bot.py'])
                subprocess.run(['pkill', '-f', 'python3 scheduler.py'])
                subprocess.run(['pkill', '-f', 'python3 payment_monitor.py'])
                time.sleep(2)
        except Exception as e:
            logger.error(f"Error checking existing processes: {e}")
        
        # 2. Start services in order
        services = [
            {
                'name': 'Main Bot',
                'command': 'python3 bot.py',
                'description': 'Starting main Telegram bot'
            },
            {
                'name': 'Scheduler',
                'command': 'python3 scheduler.py',
                'description': 'Starting ad posting scheduler'
            },
            {
                'name': 'Payment Monitor',
                'command': 'python3 payment_monitor.py',
                'description': 'Starting multi-crypto payment verification'
            }
        ]
        
        for service in services:
            self.start_service(service['name'], service['command'], service['description'])
        
        logger.info("🎉 All services started successfully!")
        logger.info("📊 Services running:")
        for name in self.processes.keys():
            logger.info(f"   • {name}")
        
        return True
    
    def run_monitoring(self):
        """Run continuous monitoring."""
        try:
            while True:
                time.sleep(60)  # Check every minute
                self.check_services()
                
                # Check if any service has stopped
                for name, process in self.processes.items():
                    if process.poll() is not None:
                        logger.warning(f"⚠️ {name} has stopped. Restarting...")
                        # Restart the service
                        if name == 'Main Bot':
                            self.start_service(name, 'python3 bot.py', 'Restarting main bot')
                        elif name == 'Scheduler':
                            self.start_service(name, 'python3 scheduler.py', 'Restarting scheduler')
                        elif name == 'Payment Monitor':
                            self.start_service(name, 'python3 payment_monitor.py', 'Restarting payment monitor')
                
        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal")
            self.stop_all_services()

def main():
    """Main function."""
    manager = ServiceManager()
    
    try:
        # Start all services
        if manager.start_all_services():
            logger.info("🚀 All services are running!")
            logger.info("💡 Press Ctrl+C to stop all services")
            
            # Start monitoring
            manager.run_monitoring()
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
        manager.stop_all_services()
        logger.info("✅ All services stopped")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        manager.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main() 