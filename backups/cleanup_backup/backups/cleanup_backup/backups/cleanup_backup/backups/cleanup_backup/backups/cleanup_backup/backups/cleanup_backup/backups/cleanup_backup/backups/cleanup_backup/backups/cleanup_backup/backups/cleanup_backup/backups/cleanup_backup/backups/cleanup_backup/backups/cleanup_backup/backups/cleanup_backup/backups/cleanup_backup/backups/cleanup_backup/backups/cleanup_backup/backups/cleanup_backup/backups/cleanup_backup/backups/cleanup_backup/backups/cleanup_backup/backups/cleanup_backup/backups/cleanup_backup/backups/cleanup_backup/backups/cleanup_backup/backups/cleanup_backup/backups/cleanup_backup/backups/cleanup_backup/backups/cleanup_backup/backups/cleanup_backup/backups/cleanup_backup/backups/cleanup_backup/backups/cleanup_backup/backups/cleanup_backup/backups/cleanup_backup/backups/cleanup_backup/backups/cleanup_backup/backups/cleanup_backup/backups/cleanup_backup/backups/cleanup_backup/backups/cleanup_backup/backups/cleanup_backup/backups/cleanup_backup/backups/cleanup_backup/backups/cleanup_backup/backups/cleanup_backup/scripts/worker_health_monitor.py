#!/usr/bin/env python3
"""
Worker Health Monitor
Monitors worker accounts to prevent bans
"""

import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv('config/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerHealthMonitor:
    def __init__(self):
        self.worker_stats = {}
        self.banned_workers = []
        
    async def check_worker_health(self, worker_index, client):
        """Check if a worker is healthy."""
        try:
            # Test basic functionality
            me = await client.get_me()
            
            # Check for restrictions
            account = await client.get_account()
            
            # Check if account is restricted
            if hasattr(account, 'restricted') and account.restricted:
                logger.warning(f"⚠️ Worker {worker_index} is restricted")
                return False
                
            # Check if account is banned
            if hasattr(account, 'deleted') and account.deleted:
                logger.error(f"❌ Worker {worker_index} is banned")
                self.banned_workers.append(worker_index)
                return False
                
            logger.info(f"✅ Worker {worker_index} is healthy")
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker {worker_index} health check failed: {e}")
            return False
    
    def update_worker_stats(self, worker_index, action):
        """Update worker usage statistics."""
        if worker_index not in self.worker_stats:
            self.worker_stats[worker_index] = {
                'posts_today': 0,
                'posts_this_hour': 0,
                'last_post_time': None,
                'total_posts': 0
            }
        
        now = datetime.now()
        stats = self.worker_stats[worker_index]
        
        # Reset hourly count if hour has passed
        if stats['last_post_time']:
            hours_since_last = (now - stats['last_post_time']).total_seconds() / 3600
            if hours_since_last >= 1:
                stats['posts_this_hour'] = 0
        
        # Update stats
        stats['posts_today'] += 1
        stats['posts_this_hour'] += 1
        stats['total_posts'] += 1
        stats['last_post_time'] = now
        
        # Check limits
        max_posts_per_hour = int(os.getenv('MAX_POSTS_PER_HOUR', 5))
        max_posts_per_day = 20
        
        if stats['posts_this_hour'] > max_posts_per_hour:
            logger.warning(f"⚠️ Worker {worker_index} exceeded hourly limit")
            return False
            
        if stats['posts_today'] > max_posts_per_day:
            logger.warning(f"⚠️ Worker {worker_index} exceeded daily limit")
            return False
            
        return True
    
    def get_available_worker(self, workers):
        """Get the healthiest available worker."""
        available_workers = []
        
        for i, worker in enumerate(workers):
            if i in self.banned_workers:
                continue
                
            stats = self.worker_stats.get(i, {})
            posts_this_hour = stats.get('posts_this_hour', 0)
            posts_today = stats.get('posts_today', 0)
            
            max_posts_per_hour = int(os.getenv('MAX_POSTS_PER_HOUR', 5))
            max_posts_per_day = 20
            
            if posts_this_hour < max_posts_per_hour and posts_today < max_posts_per_day:
                available_workers.append(i)
        
        if available_workers:
            # Return worker with least usage
            return min(available_workers, key=lambda x: self.worker_stats.get(x, {}).get('posts_this_hour', 0))
        
        return None
    
    def should_take_break(self):
        """Check if workers should take a break."""
        now = datetime.now()
        
        # Weekend break (Saturday and Sunday)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            logger.info("🌅 Weekend break - no posting today")
            return True
        
        # Night break (2 AM to 6 AM)
        if 2 <= now.hour <= 6:
            logger.info("🌙 Night break - no posting during quiet hours")
            return True
        
        return False
    
    def get_safe_delay(self):
        """Get a safe delay between posts."""
        min_delay = int(os.getenv('ANTI_BAN_DELAY_MIN', 60))
        max_delay = int(os.getenv('ANTI_BAN_DELAY_MAX', 120))
        
        # Add some randomness
        import random
        return random.randint(min_delay, max_delay)

async def main():
    """Test the worker health monitor."""
    monitor = WorkerHealthMonitor()
    
    print("🛡️ Worker Health Monitor")
    print("=" * 30)
    
    # Test break logic
    if monitor.should_take_break():
        print("⏸️ Workers should take a break")
    else:
        print("✅ Safe to post")
    
    # Test delay
    delay = monitor.get_safe_delay()
    print(f"⏱️ Safe delay: {delay} seconds")
    
    print("✅ Health monitor ready")

if __name__ == "__main__":
    asyncio.run(main()) 