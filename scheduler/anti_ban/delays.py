#!/usr/bin/env python3
"""
Anti-Ban Delays
Manages random delays and timing to avoid detection
"""

import asyncio
import random
import logging
from typing import Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DelayManager:
    """Manages delays between actions to avoid detection."""
    
    def __init__(self, min_delay: int = 30, max_delay: int = 120):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_action_time = None
        
    async def random_delay(self, min_seconds: int = None, max_seconds: int = None) -> float:
        """Wait for a random amount of time."""
        min_delay = min_seconds or self.min_delay
        max_delay = max_seconds or self.max_delay
        
        delay = random.uniform(min_delay, max_delay)
        
        logger.info(f"⏳ Waiting {delay:.1f} seconds (anti-ban delay)")
        await asyncio.sleep(delay)
        
        self.last_action_time = datetime.now()
        return delay
    
    async def post_delay(self) -> float:
        """Standard delay after posting an ad."""
        return await self.random_delay(30, 90)
    
    async def worker_switch_delay(self) -> float:
        """Delay when switching between workers."""
        return await self.random_delay(10, 30)
    
    async def group_join_delay(self) -> float:
        """Delay after joining a group."""
        return await self.random_delay(60, 180)
    
    async def error_recovery_delay(self, error_count: int) -> float:
        """Delay after encountering an error (increases with error count)."""
        base_delay = 30
        multiplier = min(error_count, 5)  # Cap at 5x multiplier
        delay = base_delay * multiplier
        
        logger.info(f"🔄 Error recovery delay: {delay} seconds (error count: {error_count})")
        await asyncio.sleep(delay)
        return delay
    
    def get_time_since_last_action(self) -> float:
        """Get time since last action in seconds."""
        if not self.last_action_time:
            return 0
        
        return (datetime.now() - self.last_action_time).total_seconds()
    
    def should_wait_longer(self) -> bool:
        """Check if we should wait longer based on recent activity."""
        time_since = self.get_time_since_last_action()
        return time_since < 60  # Wait if less than 1 minute since last action
