#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import subprocess
import signal
import time
import psutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/lightweight_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LightweightServiceManager:
    """Lightweight service manager for 1GB droplet."""
    
    def __init__(self):
        self.processes = {}
        self.memory_threshold = 800  # MB - restart if memory usage exceeds this
        
    def check_memory(self):
        """Check current memory usage."""
        memory = psutil.virtual_memory()
        return memory.used / 1024 / 1024  # Convert to MB
        
    def start_service(self, name, script, description):
        """Start a service with memory monitoring."""
        try:
            # Check if service is already running
            if name in self.processes and self.processes[name].poll() is None:
                logger.info(f"{description} is already running")
                return True
                
            # Start the service
            process = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[name] = process
            logger.info(f"Started {description} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {description}: {e}")
            return False
    
    def stop_service(self, name):
        """Stop a service."""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Force killed {name}")
            del self.processes[name]
    
    def stop_all_services(self):
        """Stop all services."""
        for name in list(self.processes.keys()):
            self.stop_service(name)
    
    def check_service_health(self):
        """Check health of all services."""
        memory_usage = self.check_memory()
        logger.info(f"Current memory usage: {memory_usage:.1f}MB")
        
        if memory_usage > self.memory_threshold:
            logger.warning(f"Memory usage high ({memory_usage:.1f}MB), restarting services...")
            self.restart_all_services()
            return False
            
        for name, process in self.processes.items():
            if process.poll() is not None:
                logger.error(f"Service {name} has stopped unexpectedly")
                return False
        return True
    
    def restart_all_services(self):
        """Restart all services."""
        logger.info("Restarting all services...")
        self.stop_all_services()
        time.sleep(2)
        self.start_essential_services()
    
    def start_essential_services(self):
        """Start only essential services for 1GB droplet."""
        logger.info("Starting essential services for 1GB droplet...")
        
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Start only the main bot and scheduler
        services = [
            ("bot", "bot.py", "Main Bot"),
            ("scheduler", "scheduler.py", "Ad Scheduler")
        ]
        
        for name, script, description in services:
            if not self.start_service(name, script, description):
                logger.error(f"Failed to start {description}")
                return False
                
        logger.info("All essential services started successfully")
        return True
    
    def run(self):
        """Run lightweight service manager."""
        logger.info("Starting Lightweight Bot Service Manager...")
        
        # Handle shutdown gracefully
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping all services...")
            self.stop_all_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start essential services
        if not self.start_essential_services():
            logger.error("Failed to start essential services")
            return
        
        # Monitor services
        try:
            while True:
                if not self.check_service_health():
                    logger.warning("Service health check failed")
                
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.stop_all_services()

if __name__ == '__main__':
    manager = LightweightServiceManager()
    manager.run() 