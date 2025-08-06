#!/usr/bin/env python3
"""
Automated Scheduler Package
Telegram ad posting automation system
"""

from .core.scheduler import AutomatedScheduler
from .config.scheduler_config import SchedulerConfig
from .config.worker_config import WorkerConfig, WorkerCredentials
from .workers.worker_client import WorkerClient
from .workers.rotation import WorkerRotator
from .anti_ban.delays import DelayManager
from .anti_ban.content_rotation import ContentRotator
from .anti_ban.ban_detection import BanDetector
from .monitoring.performance_monitor import PerformanceMonitor
from .core.posting_service import PostingService

__version__ = "1.0.0"
__author__ = "Telegram Bot Team"

__all__ = [
    'AutomatedScheduler',
    'SchedulerConfig', 
    'WorkerConfig',
    'WorkerCredentials',
    'WorkerClient',
    'WorkerRotator',
    'DelayManager',
    'ContentRotator',
    'BanDetector',
    'PerformanceMonitor',
    'PostingService'
]
