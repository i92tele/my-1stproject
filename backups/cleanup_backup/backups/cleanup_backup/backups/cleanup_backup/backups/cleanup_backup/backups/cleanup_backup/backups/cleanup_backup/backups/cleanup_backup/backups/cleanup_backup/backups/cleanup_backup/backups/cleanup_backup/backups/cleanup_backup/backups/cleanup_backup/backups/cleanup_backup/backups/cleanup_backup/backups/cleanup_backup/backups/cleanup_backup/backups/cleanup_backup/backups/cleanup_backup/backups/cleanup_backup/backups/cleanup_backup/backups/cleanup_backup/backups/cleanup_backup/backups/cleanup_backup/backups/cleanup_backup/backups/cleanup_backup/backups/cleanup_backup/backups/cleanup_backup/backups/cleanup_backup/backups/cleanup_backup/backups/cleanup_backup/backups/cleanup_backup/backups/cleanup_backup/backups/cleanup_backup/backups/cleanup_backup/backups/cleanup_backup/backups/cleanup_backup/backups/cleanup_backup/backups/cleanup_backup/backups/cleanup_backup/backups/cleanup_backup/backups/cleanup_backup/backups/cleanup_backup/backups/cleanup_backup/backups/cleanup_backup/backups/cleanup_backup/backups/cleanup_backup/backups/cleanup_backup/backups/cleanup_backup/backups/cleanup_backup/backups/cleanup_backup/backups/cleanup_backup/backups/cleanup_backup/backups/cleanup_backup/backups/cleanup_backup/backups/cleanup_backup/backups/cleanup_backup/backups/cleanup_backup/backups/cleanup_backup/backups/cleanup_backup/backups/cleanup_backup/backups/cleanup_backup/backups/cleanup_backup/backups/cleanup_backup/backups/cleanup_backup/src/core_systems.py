import logging
import asyncio
from typing import Optional

from .error_handler import initialize_error_handler, handle_errors
from .rate_limiter import initialize_rate_limiter, rate_limit
from .auto_restart import initialize_auto_restart, update_heartbeat, get_restart_stats
from .database_safety import initialize_database_safety
from .payment_timeout import initialize_payment_timeout_handler

class CoreSystems:
    """Initialize and manage all core safety systems."""
    
    def __init__(self, logger: logging.Logger, config):
        self.logger = logger
        self.config = config
        self.error_handler = None
        self.rate_limiter = None
        self.restart_manager = None
        self.health_monitor = None
        self.db_safety = None
        self.payment_timeout_handler = None
        
    async def initialize(self):
        """Initialize all core systems."""
        try:
            self.logger.info("Initializing core safety systems...")
            
            # Initialize error handler
            self.error_handler = initialize_error_handler(self.logger, self.config.admin_id)
            self.logger.info("✅ Error handler initialized")
            
            # Initialize rate limiter
            self.rate_limiter = initialize_rate_limiter(self.logger)
            await self.rate_limiter.start()
            self.logger.info("✅ Rate limiter initialized")
            
            # Initialize auto-restart system
            self.restart_manager, self.health_monitor = initialize_auto_restart(self.logger)
            await self.health_monitor.start_monitoring()
            self.logger.info("✅ Auto-restart system initialized")
            
            # Initialize database safety
            self.db_safety = initialize_database_safety(self.config.database_url, self.logger)
            await self.db_safety.initialize()
            self.logger.info("✅ Database safety layer initialized")
            
            # Initialize payment timeout handler
            self.payment_timeout_handler = initialize_payment_timeout_handler(self.logger, self.db_safety)
            await self.payment_timeout_handler.start_monitoring()
            self.logger.info("✅ Payment timeout handler initialized")
            
            self.logger.info("🎉 All core safety systems initialized successfully!")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core systems: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all core systems gracefully."""
        try:
            self.logger.info("Shutting down core safety systems...")
            
            if self.payment_timeout_handler:
                await self.payment_timeout_handler.stop_monitoring()
                self.logger.info("✅ Payment timeout handler stopped")
            
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
                self.logger.info("✅ Health monitor stopped")
            
            if self.rate_limiter:
                await self.rate_limiter.stop()
                self.logger.info("✅ Rate limiter stopped")
            
            if self.db_safety:
                await self.db_safety.close()
                self.logger.info("✅ Database safety layer closed")
            
            self.logger.info("🎉 All core safety systems shut down successfully!")
            
        except Exception as e:
            self.logger.error(f"Error during core systems shutdown: {e}")
    
    def get_system_stats(self) -> dict:
        """Get statistics from all core systems."""
        stats = {
            'error_handler': self.error_handler.get_error_stats() if self.error_handler else {},
            'rate_limiter': {
                'user_stats': self.rate_limiter.get_user_stats(0) if self.rate_limiter else {},
                'global_stats': self.rate_limiter.get_global_stats() if self.rate_limiter else {}
            },
            'auto_restart': get_restart_stats(),
            'database': self.db_safety.get_pool_stats() if self.db_safety else {},
            'payment_timeout': self.payment_timeout_handler.get_timeout_stats() if self.payment_timeout_handler else {}
        }
        return stats
    
    def update_heartbeat(self):
        """Update the system heartbeat."""
        update_heartbeat()

# Global core systems instance
core_systems = None

def initialize_core_systems(logger: logging.Logger, config):
    """Initialize the global core systems."""
    global core_systems
    core_systems = CoreSystems(logger, config)
    return core_systems

def get_core_systems() -> Optional[CoreSystems]:
    """Get the global core systems instance."""
    return core_systems

def safe_rate_limit(action: str, user_specific: bool = True):
    """Safe rate limiting decorator."""
    return rate_limit(action, user_specific)

def safe_error_handling(func):
    """Safe error handling decorator."""
    return handle_errors(func) 