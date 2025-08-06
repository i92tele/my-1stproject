#!/usr/bin/env python3
"""
Performance Monitor
Monitors scheduler performance and statistics
"""

import logging
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PostingStats:
    """Statistics for posting performance."""
    total_posts: int = 0
    successful_posts: int = 0
    failed_posts: int = 0
    total_destinations: int = 0
    average_delay: float = 0.0
    start_time: datetime = None
    
class PerformanceMonitor:
    """Monitors and tracks scheduler performance."""
    
    def __init__(self):
        self.stats = PostingStats()
        self.stats.start_time = datetime.now()
        self.cycle_stats = []
        self.error_log = []
        
    def record_post_attempt(self, destination: str, success: bool, delay: float = 0):
        """Record a posting attempt."""
        self.stats.total_posts += 1
        self.stats.total_destinations += 1
        
        if success:
            self.stats.successful_posts += 1
        else:
            self.stats.failed_posts += 1
            
        if delay > 0:
            self.stats.average_delay = (
                (self.stats.average_delay * (self.stats.total_posts - 1) + delay) / 
                self.stats.total_posts
            )
            
    def record_error(self, error: str, context: str = ""):
        """Record an error."""
        error_entry = {
            'timestamp': datetime.now(),
            'error': error,
            'context': context
        }
        self.error_log.append(error_entry)
        logger.error(f"Scheduler error: {error} - {context}")
        
    def get_success_rate(self) -> float:
        """Get posting success rate."""
        if self.stats.total_posts == 0:
            return 0.0
        return (self.stats.successful_posts / self.stats.total_posts) * 100
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        uptime = datetime.now() - self.stats.start_time
        
        return {
            'uptime_hours': uptime.total_seconds() / 3600,
            'total_posts': self.stats.total_posts,
            'successful_posts': self.stats.successful_posts,
            'failed_posts': self.stats.failed_posts,
            'success_rate': self.get_success_rate(),
            'average_delay_seconds': self.stats.average_delay,
            'total_destinations': self.stats.total_destinations,
            'recent_errors': len([e for e in self.error_log if e['timestamp'] > datetime.now() - timedelta(hours=1)])
        }
        
    def log_performance_report(self):
        """Log performance report."""
        summary = self.get_performance_summary()
        logger.info(f"Performance Report: {summary}")
