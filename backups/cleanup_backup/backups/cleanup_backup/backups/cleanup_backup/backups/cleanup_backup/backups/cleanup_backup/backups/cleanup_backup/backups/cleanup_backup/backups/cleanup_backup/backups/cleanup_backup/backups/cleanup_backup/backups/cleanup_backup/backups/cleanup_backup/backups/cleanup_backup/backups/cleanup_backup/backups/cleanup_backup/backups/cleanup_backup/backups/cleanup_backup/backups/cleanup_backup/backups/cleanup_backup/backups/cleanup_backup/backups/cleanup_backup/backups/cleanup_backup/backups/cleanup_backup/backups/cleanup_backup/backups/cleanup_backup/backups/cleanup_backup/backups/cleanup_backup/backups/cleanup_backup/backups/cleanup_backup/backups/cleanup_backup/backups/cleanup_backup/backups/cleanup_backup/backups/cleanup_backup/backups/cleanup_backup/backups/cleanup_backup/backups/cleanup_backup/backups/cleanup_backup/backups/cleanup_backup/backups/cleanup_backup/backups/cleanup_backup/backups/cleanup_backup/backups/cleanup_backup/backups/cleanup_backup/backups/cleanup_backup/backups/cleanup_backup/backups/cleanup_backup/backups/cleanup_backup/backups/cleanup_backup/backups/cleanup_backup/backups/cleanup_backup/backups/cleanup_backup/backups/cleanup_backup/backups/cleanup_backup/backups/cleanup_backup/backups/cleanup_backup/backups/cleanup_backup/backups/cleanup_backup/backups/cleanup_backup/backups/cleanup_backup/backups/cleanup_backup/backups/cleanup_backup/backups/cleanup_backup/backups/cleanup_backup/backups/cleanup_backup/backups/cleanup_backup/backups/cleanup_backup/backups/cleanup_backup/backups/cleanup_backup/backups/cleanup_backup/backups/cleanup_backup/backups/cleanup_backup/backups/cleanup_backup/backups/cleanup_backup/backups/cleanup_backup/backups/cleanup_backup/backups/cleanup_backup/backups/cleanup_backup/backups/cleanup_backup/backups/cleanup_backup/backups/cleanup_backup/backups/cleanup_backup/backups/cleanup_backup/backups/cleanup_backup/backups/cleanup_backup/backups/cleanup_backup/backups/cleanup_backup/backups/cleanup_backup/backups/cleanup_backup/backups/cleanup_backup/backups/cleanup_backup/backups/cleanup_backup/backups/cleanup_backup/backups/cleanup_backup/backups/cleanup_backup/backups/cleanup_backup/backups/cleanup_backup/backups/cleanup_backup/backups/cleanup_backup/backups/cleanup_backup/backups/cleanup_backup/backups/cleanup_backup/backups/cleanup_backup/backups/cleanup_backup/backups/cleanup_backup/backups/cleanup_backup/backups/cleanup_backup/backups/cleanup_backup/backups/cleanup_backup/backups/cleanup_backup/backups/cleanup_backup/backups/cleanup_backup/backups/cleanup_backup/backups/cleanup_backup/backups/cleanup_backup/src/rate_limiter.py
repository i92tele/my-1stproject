import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

class RateLimiter:
    """Production-ready rate limiting system."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.user_actions: Dict[int, Dict[str, List[datetime]]] = defaultdict(lambda: defaultdict(list))
        self.global_actions: Dict[str, List[datetime]] = defaultdict(list)
        self.cleanup_task = None
        
    async def start(self):
        """Start the rate limiter cleanup task."""
        self.cleanup_task = asyncio.create_task(self._cleanup_old_records())
        self.logger.info("Rate limiter started")
    
    async def stop(self):
        """Stop the rate limiter."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Rate limiter stopped")
    
    def check_rate_limit(self, user_id: int, action: str, max_actions: int, window_seconds: int) -> bool:
        """Check if user is within rate limits for a specific action."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)
        
        # Clean old records for this user/action
        self.user_actions[user_id][action] = [
            time for time in self.user_actions[user_id][action]
            if time > cutoff_time
        ]
        
        # Check if user has exceeded limit
        if len(self.user_actions[user_id][action]) >= max_actions:
            self.logger.warning(f"Rate limit exceeded for user {user_id}, action {action}")
            return False
        
        # Record this action
        self.user_actions[user_id][action].append(now)
        return True
    
    def check_global_rate_limit(self, action: str, max_actions: int, window_seconds: int) -> bool:
        """Check global rate limits (across all users)."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=window_seconds)
        
        # Clean old records
        self.global_actions[action] = [
            time for time in self.global_actions[action]
            if time > cutoff_time
        ]
        
        # Check if global limit exceeded
        if len(self.global_actions[action]) >= max_actions:
            self.logger.warning(f"Global rate limit exceeded for action {action}")
            return False
        
        # Record this action
        self.global_actions[action].append(now)
        return True
    
    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Get rate limit statistics for a user."""
        stats = {}
        for action, times in self.user_actions[user_id].items():
            # Count actions in last hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_actions = [time for time in times if time > cutoff_time]
            stats[action] = len(recent_actions)
        return stats
    
    def get_global_stats(self) -> Dict[str, int]:
        """Get global rate limit statistics."""
        stats = {}
        for action, times in self.global_actions.items():
            # Count actions in last hour
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_actions = [time for time in times if time > cutoff_time]
            stats[action] = len(recent_actions)
        return stats
    
    async def _cleanup_old_records(self):
        """Periodically clean up old rate limit records."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                now = datetime.now()
                cutoff_time = now - timedelta(hours=24)  # Keep 24 hours of data
                
                # Clean user actions
                for user_id in list(self.user_actions.keys()):
                    for action in list(self.user_actions[user_id].keys()):
                        self.user_actions[user_id][action] = [
                            time for time in self.user_actions[user_id][action]
                            if time > cutoff_time
                        ]
                        # Remove empty action lists
                        if not self.user_actions[user_id][action]:
                            del self.user_actions[user_id][action]
                    # Remove users with no actions
                    if not self.user_actions[user_id]:
                        del self.user_actions[user_id]
                
                # Clean global actions
                for action in list(self.global_actions.keys()):
                    self.global_actions[action] = [
                        time for time in self.global_actions[action]
                        if time > cutoff_time
                    ]
                    # Remove empty action lists
                    if not self.global_actions[action]:
                        del self.global_actions[action]
                
                self.logger.debug("Rate limiter cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in rate limiter cleanup: {e}")

# Predefined rate limits for common actions
RATE_LIMITS = {
    'send_message': {'max_actions': 5, 'window_seconds': 60},  # 5 messages per minute
    'add_destination': {'max_actions': 3, 'window_seconds': 300},  # 3 destinations per 5 minutes
    'buy_slot': {'max_actions': 2, 'window_seconds': 600},  # 2 purchases per 10 minutes
    'admin_command': {'max_actions': 10, 'window_seconds': 60},  # 10 admin commands per minute
    'payment_request': {'max_actions': 3, 'window_seconds': 300},  # 3 payment requests per 5 minutes
    'worker_action': {'max_actions': 20, 'window_seconds': 3600},  # 20 worker actions per hour
}

# Global rate limiter instance
rate_limiter = None

def initialize_rate_limiter(logger: logging.Logger):
    """Initialize the global rate limiter."""
    global rate_limiter
    rate_limiter = RateLimiter(logger)
    return rate_limiter

def rate_limit(action: str, user_specific: bool = True):
    """Decorator to apply rate limiting to functions."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if rate_limiter is None:
                # Fallback if not initialized
                return await func(*args, **kwargs)
            
            # Get user_id from args (assuming first arg is Update)
            user_id = None
            if args and hasattr(args[0], 'effective_user'):
                user_id = args[0].effective_user.id
            
            # Get rate limit config
            limit_config = RATE_LIMITS.get(action, {'max_actions': 5, 'window_seconds': 60})
            
            # Check rate limits
            if user_specific and user_id:
                if not rate_limiter.check_rate_limit(
                    user_id, action, 
                    limit_config['max_actions'], 
                    limit_config['window_seconds']
                ):
                    return "Rate limit exceeded. Please wait before trying again."
            
            # Check global rate limit
            if not rate_limiter.check_global_rate_limit(
                action, 
                limit_config['max_actions'] * 10,  # Global limit is 10x user limit
                limit_config['window_seconds']
            ):
                return "Service temporarily unavailable due to high traffic. Please try again later."
            
            # Execute function
            return await func(*args, **kwargs)
        return wrapper
    return decorator 