#!/usr/bin/env python3
"""
Scheduler Configuration
Manages all scheduler settings and parameters
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class SchedulerConfig:
    """Scheduler configuration settings."""
    
    # Timing settings
    posting_interval_minutes: int = 60  # How often to run posting cycle
    max_posts_per_cycle: int = 50       # Max posts per cycle
    worker_cooldown_minutes: int = 30   # Cooldown between worker usage
    
    # Anti-ban settings
    min_delay_seconds: int = 30         # Minimum delay between posts
    max_delay_seconds: int = 120        # Maximum delay between posts
    max_uses_per_worker_per_hour: int = 10  # Max uses per worker per hour
    
    # Group management
    max_groups_per_ad: int = 10         # Max groups to post to per ad
    auto_join_groups: bool = True       # Auto-join groups if not member
    
    # Error handling
    max_retries_per_post: int = 3       # Max retries for failed posts
    retry_delay_minutes: int = 5        # Delay between retries
    
    # Monitoring
    enable_performance_tracking: bool = True
    enable_alert_system: bool = True
    log_all_activities: bool = True

def load_scheduler_config() -> SchedulerConfig:
    """Load scheduler configuration from environment variables."""
    
    return SchedulerConfig(
        posting_interval_minutes=int(os.getenv('SCHEDULER_POSTING_INTERVAL', '60')),
        max_posts_per_cycle=int(os.getenv('SCHEDULER_MAX_POSTS_PER_CYCLE', '50')),
        worker_cooldown_minutes=int(os.getenv('SCHEDULER_WORKER_COOLDOWN', '30')),
        min_delay_seconds=int(os.getenv('SCHEDULER_MIN_DELAY', '30')),
        max_delay_seconds=int(os.getenv('SCHEDULER_MAX_DELAY', '120')),
        max_uses_per_worker_per_hour=int(os.getenv('SCHEDULER_MAX_WORKER_USES', '10')),
        max_groups_per_ad=int(os.getenv('SCHEDULER_MAX_GROUPS_PER_AD', '10')),
        auto_join_groups=os.getenv('SCHEDULER_AUTO_JOIN_GROUPS', 'true').lower() == 'true',
        max_retries_per_post=int(os.getenv('SCHEDULER_MAX_RETRIES', '3')),
        retry_delay_minutes=int(os.getenv('SCHEDULER_RETRY_DELAY', '5')),
        enable_performance_tracking=os.getenv('SCHEDULER_PERFORMANCE_TRACKING', 'true').lower() == 'true',
        enable_alert_system=os.getenv('SCHEDULER_ALERT_SYSTEM', 'true').lower() == 'true',
        log_all_activities=os.getenv('SCHEDULER_LOG_ACTIVITIES', 'true').lower() == 'true'
    )
