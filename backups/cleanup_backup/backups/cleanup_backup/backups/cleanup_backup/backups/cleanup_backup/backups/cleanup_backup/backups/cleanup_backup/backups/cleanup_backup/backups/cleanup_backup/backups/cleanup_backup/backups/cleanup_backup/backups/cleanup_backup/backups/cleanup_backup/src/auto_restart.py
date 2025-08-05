import asyncio
import logging
import signal
import sys
import os
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional, List

class AutoRestartManager:
    """Production-ready auto-restart system."""
    
    def __init__(self, logger: logging.Logger, max_restarts: int = 5, restart_window_hours: int = 1):
        self.logger = logger
        self.max_restarts = max_restarts
        self.restart_window_hours = restart_window_hours
        self.restart_times: List[datetime] = []
        self.is_shutting_down = False
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.logger.info("Signal handlers configured")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_shutting_down = True
        # Let the main loop handle the shutdown
    
    def can_restart(self) -> bool:
        """Check if we can restart based on restart limits."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.restart_window_hours)
        
        # Remove old restart times
        self.restart_times = [time for time in self.restart_times if time > cutoff_time]
        
        # Check if we've exceeded restart limit
        if len(self.restart_times) >= self.max_restarts:
            self.logger.error(f"Maximum restarts ({self.max_restarts}) exceeded in {self.restart_window_hours} hour window")
            return False
        
        return True
    
    def record_restart(self):
        """Record a restart attempt."""
        self.restart_times.append(datetime.now())
        self.logger.warning(f"Restart recorded. Total restarts in window: {len(self.restart_times)}")
    
    async def restart_bot(self):
        """Restart the bot process."""
        if not self.can_restart():
            self.logger.critical("Cannot restart - maximum restarts exceeded")
            return False
        
        self.record_restart()
        self.logger.info("Initiating bot restart...")
        
        try:
            # Get current script path
            script_path = sys.argv[0]
            
            # Restart the process
            os.execv(sys.executable, ['python'] + sys.argv)
            
        except Exception as e:
            self.logger.error(f"Failed to restart bot: {e}")
            return False
        
        return True
    
    def get_restart_stats(self) -> dict:
        """Get restart statistics."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.restart_window_hours)
        
        recent_restarts = [time for time in self.restart_times if time > cutoff_time]
        
        return {
            'total_restarts': len(self.restart_times),
            'recent_restarts': len(recent_restarts),
            'max_restarts': self.max_restarts,
            'window_hours': self.restart_window_hours,
            'can_restart': self.can_restart(),
            'last_restart': self.restart_times[-1] if self.restart_times else None
        }

class HealthMonitor:
    """Monitor bot health and trigger restarts if needed."""
    
    def __init__(self, logger: logging.Logger, restart_manager: AutoRestartManager):
        self.logger = logger
        self.restart_manager = restart_manager
        self.last_heartbeat = datetime.now()
        self.heartbeat_interval = 300  # 5 minutes
        self.max_heartbeat_age = 600  # 10 minutes
        self.monitor_task = None
        
    async def start_monitoring(self):
        """Start the health monitoring task."""
        self.monitor_task = asyncio.create_task(self._monitor_health())
        self.logger.info("Health monitor started")
    
    async def stop_monitoring(self):
        """Stop the health monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health monitor stopped")
    
    def update_heartbeat(self):
        """Update the heartbeat timestamp."""
        self.last_heartbeat = datetime.now()
    
    async def _monitor_health(self):
        """Monitor bot health and restart if needed."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check if heartbeat is too old
                age = (datetime.now() - self.last_heartbeat).total_seconds()
                
                if age > self.max_heartbeat_age:
                    self.logger.warning(f"Heartbeat too old ({age}s), considering restart")
                    
                    if self.restart_manager.can_restart():
                        self.logger.error("Bot appears unresponsive, initiating restart")
                        await self.restart_manager.restart_bot()
                    else:
                        self.logger.critical("Bot unresponsive but restart limit exceeded")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")

# Global instances
restart_manager = None
health_monitor = None

def initialize_auto_restart(logger: logging.Logger):
    """Initialize the auto-restart system."""
    global restart_manager, health_monitor
    
    restart_manager = AutoRestartManager(logger)
    health_monitor = HealthMonitor(logger, restart_manager)
    
    # Setup signal handlers
    restart_manager.setup_signal_handlers()
    
    return restart_manager, health_monitor

def update_heartbeat():
    """Update the heartbeat (call this periodically in your main loop)."""
    if health_monitor:
        health_monitor.update_heartbeat()

def get_restart_stats() -> dict:
    """Get restart statistics."""
    if restart_manager:
        return restart_manager.get_restart_stats()
    return {} 