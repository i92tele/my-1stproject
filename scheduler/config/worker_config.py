#!/usr/bin/env python3
"""
Worker Configuration
Manages worker account settings and credentials
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WorkerCredentials:
    """Worker account credentials."""
    worker_id: int
    api_id: str
    api_hash: str
    phone: str
    session_file: str
    is_active: bool = True

class WorkerConfig:
    """Manages worker account configuration."""
    
    def __init__(self):
        self.workers: List[WorkerCredentials] = []
        self.sessions_dir = "sessions"
        
    def load_workers_from_env(self) -> List[WorkerCredentials]:
        """Load worker credentials from environment variables."""
        workers = []
        
        # Check for worker credentials in environment
        worker_count = 0
        for i in range(1, 11):  # Support up to 10 workers
            api_id = os.getenv(f'WORKER_{i}_API_ID')
            api_hash = os.getenv(f'WORKER_{i}_API_HASH')
            phone = os.getenv(f'WORKER_{i}_PHONE')
            
            if api_id and api_hash and phone:
                worker = WorkerCredentials(
                    worker_id=i,
                    api_id=api_id,
                    api_hash=api_hash,
                    phone=phone,
                    session_file=f"{self.sessions_dir}/worker_{i}.session"
                )
                workers.append(worker)
                worker_count += 1
                logger.info(f"Loaded worker {i} credentials")
                
        logger.info(f"Loaded {worker_count} worker accounts")
        return workers
        
    def get_active_workers(self) -> List[WorkerCredentials]:
        """Get list of active workers."""
        return [w for w in self.workers if w.is_active]
        
    def deactivate_worker(self, worker_id: int):
        """Deactivate a worker."""
        for worker in self.workers:
            if worker.worker_id == worker_id:
                worker.is_active = False
                logger.warning(f"Deactivated worker {worker_id}")
                break
                
    def activate_worker(self, worker_id: int):
        """Activate a worker."""
        for worker in self.workers:
            if worker.worker_id == worker_id:
                worker.is_active = True
                logger.info(f"Activated worker {worker_id}")
                break
                
    def get_worker_by_id(self, worker_id: int) -> Optional[WorkerCredentials]:
        """Get worker by ID."""
        for worker in self.workers:
            if worker.worker_id == worker_id:
                return worker
        return None
