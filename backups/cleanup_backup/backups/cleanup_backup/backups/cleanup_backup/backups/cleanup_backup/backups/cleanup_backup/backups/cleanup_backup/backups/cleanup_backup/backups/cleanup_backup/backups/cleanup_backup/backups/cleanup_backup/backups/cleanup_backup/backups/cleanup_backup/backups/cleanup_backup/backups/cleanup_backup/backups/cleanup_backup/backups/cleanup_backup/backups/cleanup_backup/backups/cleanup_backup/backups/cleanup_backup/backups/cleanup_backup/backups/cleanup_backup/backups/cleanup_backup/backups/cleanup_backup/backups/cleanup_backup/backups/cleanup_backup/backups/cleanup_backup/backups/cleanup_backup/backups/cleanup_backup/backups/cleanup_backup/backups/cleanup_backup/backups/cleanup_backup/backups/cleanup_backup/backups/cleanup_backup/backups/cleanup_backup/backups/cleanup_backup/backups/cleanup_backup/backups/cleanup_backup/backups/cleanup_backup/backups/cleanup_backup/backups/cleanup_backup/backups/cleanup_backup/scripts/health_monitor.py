#!/usr/bin/env python3
import os
import time
import subprocess
import signal
import psutil
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotHealthMonitor:
    def __init__(self):
        self.bot_process = None
        self.last_activity = datetime.now()
        self.max_idle_time = 300  # 5 minutes
        self.check_interval = 60   # 1 minute
        self.restart_count = 0
        self.max_restarts = 5
        
    def start_bot(self):
        """Start the bot process."""
        try:
            if self.bot_process and self.bot_process.poll() is None:
                logger.warning("Bot is already running")
                return
                
            logger.info("Starting bot process...")
            self.bot_process = subprocess.Popen(
                ['python3', 'bot.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            self.last_activity = datetime.now()
            logger.info(f"Bot started with PID: {self.bot_process.pid}")
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            
    def stop_bot(self):
        """Stop the bot process gracefully."""
        if self.bot_process and self.bot_process.poll() is None:
            logger.info("Stopping bot process...")
            try:
                # Try graceful shutdown first
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Bot didn't stop gracefully, forcing kill...")
                self.bot_process.kill()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
                
    def check_bot_health(self):
        """Check if the bot is healthy and responsive."""
        try:
            # Check if process is running
            if not self.bot_process or self.bot_process.poll() is not None:
                logger.warning("Bot process is not running")
                return False
                
            # Check log file for recent activity
            log_file = 'logs/bot.log'
            if os.path.exists(log_file):
                # Check if log file was modified in last 2 minutes
                log_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if datetime.now() - log_mtime > timedelta(minutes=2):
                    logger.warning("Bot log file hasn't been updated recently")
                    return False
                    
            # Check for lock file
            lock_file = 'bot.lock'
            if os.path.exists(lock_file):
                # Check if lock file is stale (older than 10 minutes)
                lock_mtime = datetime.fromtimestamp(os.path.getmtime(lock_file))
                if datetime.now() - lock_mtime > timedelta(minutes=10):
                    logger.warning("Stale lock file detected")
                    os.remove(lock_file)
                    return False
                    
            # Check CPU and memory usage
            try:
                process = psutil.Process(self.bot_process.pid)
                cpu_percent = process.cpu_percent()
                memory_percent = process.memory_percent()
                
                if cpu_percent > 80:  # High CPU usage
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                    return False
                    
                if memory_percent > 70:  # High memory usage
                    logger.warning(f"High memory usage: {memory_percent}%")
                    return False
                    
            except psutil.NoSuchProcess:
                logger.warning("Bot process not found in psutil")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking bot health: {e}")
            return False
            
    def restart_bot(self):
        """Restart the bot process."""
        if self.restart_count >= self.max_restarts:
            logger.error(f"Maximum restart attempts ({self.max_restarts}) reached. Stopping monitor.")
            return False
            
        logger.info(f"Restarting bot (attempt {self.restart_count + 1}/{self.max_restarts})")
        self.stop_bot()
        time.sleep(5)  # Wait for cleanup
        self.start_bot()
        self.restart_count += 1
        return True
        
    def monitor(self):
        """Main monitoring loop."""
        logger.info("Starting bot health monitor...")
        self.start_bot()
        
        while True:
            try:
                if not self.check_bot_health():
                    logger.warning("Bot health check failed")
                    if not self.restart_bot():
                        break
                else:
                    # Reset restart count if bot is healthy
                    if self.restart_count > 0:
                        logger.info("Bot is healthy again, resetting restart count")
                        self.restart_count = 0
                        
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down monitor...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
                
        self.stop_bot()
        logger.info("Bot health monitor stopped")

if __name__ == '__main__':
    monitor = BotHealthMonitor()
    monitor.monitor() 