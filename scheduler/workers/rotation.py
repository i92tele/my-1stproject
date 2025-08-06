#!/usr/bin/env python3
"""
Worker Rotation
Manages rotation between worker accounts
"""

import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .worker_client import WorkerClient

logger = logging.getLogger(__name__)

class WorkerRotator:
    """Manages rotation between worker accounts."""
    
    def __init__(self, workers: List[WorkerClient]):
        self.workers = workers
        self.current_worker_index = 0
        self.worker_stats = {i: {'posts': 0, 'bans': 0, 'last_used': None} for i in range(len(workers))}
        
    def get_next_worker(self) -> Optional[WorkerClient]:
        """Get next available worker using round-robin."""
        if not self.workers:
            return None
            
        # Find next available worker
        attempts = 0
        while attempts < len(self.workers):
            worker = self.workers[self.current_worker_index]
            
            if self.is_worker_available(worker):
                self.worker_stats[self.current_worker_index]['last_used'] = datetime.now()
                self.worker_stats[self.current_worker_index]['posts'] += 1
                self.current_worker_index = (self.current_worker_index + 1) % len(self.workers)
                return worker
                
            self.current_worker_index = (self.current_worker_index + 1) % len(self.workers)
            attempts += 1
            
        return None
        
    def is_worker_available(self, worker: WorkerClient) -> bool:
        """Check if worker is available for posting."""
        if not worker.is_connected:
            return False
            
        # Check if worker is banned
        if worker.is_banned:
            return False
            
        # Check cooldown period
        last_used = self.worker_stats[self.current_worker_index]['last_used']
        if last_used:
            cooldown_minutes = 30
            if datetime.now() - last_used < timedelta(minutes=cooldown_minutes):
                return False
                
        return True
        
    def mark_worker_banned(self, worker: WorkerClient, ban_type: str):
        """Mark worker as banned."""
        worker_index = self.workers.index(worker)
        self.worker_stats[worker_index]['bans'] += 1
        
        if ban_type == 'user_banned':
            worker.is_banned = True
            logger.warning(f"Worker {worker_index} permanently banned")
        else:
            # Temporary ban - will be available after cooldown
            logger.warning(f"Worker {worker_index} temporarily banned: {ban_type}")
            
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics for all workers."""
        return {
            'total_workers': len(self.workers),
            'available_workers': sum(1 for w in self.workers if self.is_worker_available(w)),
            'banned_workers': sum(1 for w in self.workers if w.is_banned),
            'worker_details': self.worker_stats
        }
