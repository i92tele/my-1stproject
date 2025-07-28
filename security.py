from datetime import datetime, timedelta
from typing import Optional, Dict
import secrets
import logging

class SecurityManager:
    """Basic security management for the bot."""
    
    def __init__(self, config, db, logger):
        self.config = config
        self.db = db
        self.logger = logger
        self.rate_limiters = {}
    
    async def check_rate_limit(self, user_id: int, action: str, limit: int = 10, window: int = 60) -> bool:
        """Check if user has exceeded rate limit."""
        key = f"{user_id}:{action}"
        current_time = datetime.now()
        
        if key not in self.rate_limiters:
            self.rate_limiters[key] = []
        
        # Clean old entries
        self.rate_limiters[key] = [
            timestamp for timestamp in self.rate_limiters[key]
            if (current_time - timestamp).seconds < window
        ]
        
        if len(self.rate_limiters[key]) >= limit:
            return False
            
        self.rate_limiters[key].append(current_time)
        return True
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input."""
        if not text:
            return ""
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Limit length
        text = text[:max_length]
        
        return text
    
    async def log_security_event(self, event_data: Dict) -> None:
        """Log security event."""
        self.logger.info(f"Security event: {event_data}")