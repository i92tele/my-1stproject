#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import signal
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/startup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_stale_files():
    """Clean up stale files that might cause issues."""
    stale_files = ['bot.lock']
    
    for file in stale_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                logger.info(f"Removed stale file: {file}")
            except Exception as e:
                logger.error(f"Failed to remove {file}: {e}")

def check_dependencies():
    """Check if all required dependencies are available."""
    required_files = [
        'bot.py',
        'database.py',
        'config.py',
        'commands/',
        'config/.env'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False
    
    return True

def run_fixes():
    """Run the scheduler fixes before starting."""
    try:
        logger.info("Running scheduler fixes...")
        result = subprocess.run(['python3', 'fix_scheduler_stuck.py'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logger.info("Scheduler fixes completed successfully")
        else:
            logger.warning(f"Scheduler fixes had issues: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.warning("Scheduler fixes timed out")
    except Exception as e:
        logger.error(f"Error running scheduler fixes: {e}")

def start_services():
    """Start all required services."""
    processes = []
    
    try:
        # Start the main bot
        logger.info("Starting main bot...")
        bot_process = subprocess.Popen(
            ['python3', 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(('bot', bot_process))
        logger.info(f"Bot started with PID: {bot_process.pid}")
        
        # Start the scheduler
        logger.info("Starting scheduler...")
        scheduler_process = subprocess.Popen(
            ['python3', 'scheduler.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(('scheduler', scheduler_process))
        logger.info(f"Scheduler started with PID: {scheduler_process.pid}")
        
        # Start the health monitor
        logger.info("Starting health monitor...")
        monitor_process = subprocess.Popen(
            ['python3', 'health_monitor.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(('monitor', monitor_process))
        logger.info(f"Health monitor started with PID: {monitor_process.pid}")
        
        return processes
        
    except Exception as e:
        logger.error(f"Error starting services: {e}")
        # Clean up any started processes
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        return []

def monitor_processes(processes):
    """Monitor all processes and restart if needed."""
    logger.info("Monitoring processes...")
    
    while True:
        try:
            for name, process in processes:
                if process.poll() is not None:
                    logger.warning(f"{name} process died, restarting...")
                    # Restart the process
                    if name == 'bot':
                        new_process = subprocess.Popen(
                            ['python3', 'bot.py'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    elif name == 'scheduler':
                        new_process = subprocess.Popen(
                            ['python3', 'scheduler.py'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    elif name == 'monitor':
                        new_process = subprocess.Popen(
                            ['python3', 'health_monitor.py'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    
                    processes.remove((name, process))
                    processes.append((name, new_process))
                    logger.info(f"{name} restarted with PID: {new_process.pid}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in process monitoring: {e}")
            time.sleep(30)

def cleanup_processes(processes):
    """Clean up all processes."""
    logger.info("Cleaning up processes...")
    
    for name, process in processes:
        try:
            logger.info(f"Stopping {name} process...")
            process.terminate()
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning(f"Force killing {name} process...")
            process.kill()
        except Exception as e:
            logger.error(f"Error stopping {name} process: {e}")

def main():
    """Main startup function."""
    logger.info("Starting bot services safely...")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependencies check failed. Exiting.")
        return
    
    # Clean up stale files
    cleanup_stale_files()
    
    # Run fixes
    run_fixes()
    
    # Start services
    processes = start_services()
    if not processes:
        logger.error("Failed to start services. Exiting.")
        return
    
    try:
        # Monitor processes
        monitor_processes(processes)
    finally:
        # Clean up on exit
        cleanup_processes(processes)
        cleanup_stale_files()
        logger.info("All services stopped.")

if __name__ == '__main__':
    main() 