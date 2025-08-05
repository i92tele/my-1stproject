#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import subprocess
import signal
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/services.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages all bot services."""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_service(self, name: str, script: str, description: str):
        """Start a service in a separate process."""
        try:
            logger.info(f"🚀 Starting {description}...")
            process = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = {
                'process': process,
                'script': script,
                'description': description,
                'start_time': datetime.now()
            }
            logger.info(f"✅ {description} started (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start {description}: {e}")
            return False
    
    def stop_service(self, name: str):
        """Stop a specific service."""
        if name in self.processes:
            process_info = self.processes[name]
            process = process_info['process']
            
            try:
                logger.info(f"🛑 Stopping {process_info['description']}...")
                process.terminate()
                process.wait(timeout=10)
                logger.info(f"✅ {process_info['description']} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ Force killing {process_info['description']}")
                process.kill()
            except Exception as e:
                logger.error(f"❌ Error stopping {process_info['description']}: {e}")
            
            del self.processes[name]
    
    def stop_all_services(self):
        """Stop all running services."""
        logger.info("🛑 Stopping all services...")
        for name in list(self.processes.keys()):
            self.stop_service(name)
    
    def check_service_health(self):
        """Check if all services are running properly."""
        healthy_services = []
        failed_services = []
        
        for name, info in self.processes.items():
            process = info['process']
            if process.poll() is None:  # Process is still running
                healthy_services.append(name)
            else:
                failed_services.append(name)
                logger.warning(f"⚠️ {info['description']} has stopped unexpectedly")
        
        return healthy_services, failed_services
    
    def restart_failed_services(self):
        """Restart any services that have failed."""
        healthy_services, failed_services = self.check_service_health()
        
        for failed_service in failed_services:
            info = self.processes[failed_service]
            logger.info(f"🔄 Restarting {info['description']}...")
            
            # Remove from processes dict
            del self.processes[failed_service]
            
            # Restart the service
            self.start_service(failed_service, info['script'], info['description'])
    
    def run(self):
        """Run all services and monitor them."""
        logger.info("🚀 Starting AutoFarming Bot Services...")
        
        # Start all services
        services = [
            ("bot", "bot.py", "Main Bot"),
            ("scheduler", "scheduler.py", "Ad Scheduler"),
            ("maintenance", "maintenance.py", "Maintenance Service"),
            ("payment_monitor", "payment_monitor.py", "Payment Monitor")
        ]
        
        for name, script, description in services:
            self.start_service(name, script, description)
            time.sleep(2)  # Small delay between starts
        
        # Monitor services
        try:
            while self.running:
                time.sleep(30)  # Check every 30 seconds
                
                # Check service health
                healthy_services, failed_services = self.check_service_health()
                
                if failed_services:
                    logger.warning(f"⚠️ Failed services: {failed_services}")
                    self.restart_failed_services()
                else:
                    logger.info(f"✅ All services healthy: {healthy_services}")
                
        except KeyboardInterrupt:
            logger.info("⏹️ Received shutdown signal")
        except Exception as e:
            logger.error(f"❌ Service manager error: {e}")
        finally:
            self.stop_all_services()
            logger.info("👋 All services stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum}")
    # The service manager will handle the shutdown

if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Start service manager
    manager = ServiceManager()
    manager.run() 