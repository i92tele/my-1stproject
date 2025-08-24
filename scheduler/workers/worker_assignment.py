import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WorkerAssignmentService:
    """Service for intelligent worker assignment to ad slots."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_best_available_worker(self) -> Optional[Dict]:
        """Get the best available worker based on safety score and usage."""
        try:
            available_workers = await self.db.get_available_workers()
            
            if not available_workers:
                logger.warning("No available workers found")
                return None
            
            # Enhanced sorting algorithm for better worker selection
            sorted_workers = sorted(
                available_workers,
                key=lambda w: (
                    # Primary: Avoid workers near their limits (safety first)
                    -(w.get('hourly_posts', 0) / max(w.get('hourly_limit', 15), 1)),  # Lower usage percentage first
                    -(w.get('daily_posts', 0) / max(w.get('daily_limit', 150), 1)),   # Lower daily usage first
                    # Secondary: Prefer workers with good health
                    w.get('success_rate', 100.0),     # Higher success rate first
                    -w.get('ban_count', 0),           # Lower ban count first
                    -w.get('error_count', 0),         # Lower error count first
                    # Tertiary: Load balancing
                    w.get('hourly_posts', 0),         # Prefer less used workers
                )
            )
            
            best_worker = sorted_workers[0]
            usage_percent = (best_worker.get('hourly_posts', 0) / max(best_worker.get('hourly_limit', 15), 1)) * 100
            
            logger.info(f"Selected worker {best_worker['worker_id']} - Usage: {usage_percent:.1f}%, Success: {best_worker.get('success_rate', 100.0):.1f}%")
            
            return best_worker
            
        except Exception as e:
            logger.error(f"Error getting best available worker: {e}")
            return None
    
    async def assign_worker_to_ad_slot(self, ad_slot_id: int) -> Optional[Dict]:
        """Assign the best available worker to a specific ad slot."""
        worker = await self.get_best_available_worker()
        
        if worker:
            logger.info(f"Assigned worker {worker['worker_id']} to ad slot {ad_slot_id}")
            return worker
        else:
            logger.error(f"No available workers for ad slot {ad_slot_id}")
            return None
    
    async def check_worker_capacity(self) -> Dict:
        """Check overall worker capacity and create warnings if needed."""
        try:
            available_workers = await self.db.get_available_workers()
            total_workers = await self.db.get_all_workers()
            
            capacity_info = {
                'available_workers': len(available_workers),
                'total_workers': len(total_workers),
                'utilization_percent': 0,
                'warnings': []
            }
            
            if total_workers:
                capacity_info['utilization_percent'] = (
                    (len(total_workers) - len(available_workers)) / len(total_workers) * 100
                )
            
            # Create warnings based on capacity
            if len(available_workers) == 0:
                await self._create_capacity_warning("NO_WORKERS_AVAILABLE", 
                    "All workers are at their limits. Consider adding more workers or waiting for limits to reset.")
                capacity_info['warnings'].append("No workers available")
            
            elif len(available_workers) <= 2:
                await self._create_capacity_warning("LOW_WORKER_CAPACITY", 
                    f"Only {len(available_workers)} workers available. Consider adding more workers.")
                capacity_info['warnings'].append(f"Low capacity: {len(available_workers)} workers")
            
            elif capacity_info['utilization_percent'] > 80:
                await self._create_capacity_warning("HIGH_UTILIZATION", 
                    f"Worker utilization at {capacity_info['utilization_percent']:.1f}%. Consider adding more workers.")
                capacity_info['warnings'].append(f"High utilization: {capacity_info['utilization_percent']:.1f}%")
            
            return capacity_info
            
        except Exception as e:
            logger.error(f"Error checking worker capacity: {e}")
            return {
                'available_workers': 0,
                'total_workers': 0,
                'utilization_percent': 0,
                'warnings': [f"Error checking capacity: {e}"]
            }
    
    async def _create_capacity_warning(self, warning_type: str, message: str):
        """Create an admin warning about worker capacity."""
        try:
            await self.db.create_admin_warning(
                warning_type=warning_type,
                message=message,
                severity="medium"
            )
            logger.warning(f"Created capacity warning: {message}")
        except Exception as e:
            logger.error(f"Error creating capacity warning: {e}")
    
    async def get_worker_status_summary(self) -> Dict:
        """Get a summary of all worker statuses."""
        try:
            workers = await self.db.get_all_workers()
            available_workers = await self.db.get_available_workers()
            
            total_hourly_posts = 0
            total_daily_posts = 0
            total_safety_score = 0
            available_count = 0
            
            for worker in workers:
                usage = await self.db.get_worker_usage(worker['worker_id'])
                if usage:
                    total_hourly_posts += usage.get('hourly_posts', 0)
                    total_daily_posts += usage.get('daily_posts', 0)
                    total_safety_score += usage.get('safety_score', 100.0)
                
                if any(w['worker_id'] == worker['worker_id'] for w in available_workers):
                    available_count += 1
            
            return {
                'total_workers': len(workers),
                'available_workers': available_count,
                'total_hourly_posts': total_hourly_posts,
                'total_daily_posts': total_daily_posts,
                'average_safety_score': total_safety_score / len(workers) if workers else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting worker status summary: {e}")
            return {
                'total_workers': 0,
                'available_workers': 0,
                'total_hourly_posts': 0,
                'total_daily_posts': 0,
                'average_safety_score': 0
            }
