import logging
from typing import Dict, Any
from src.services.worker_manager import WorkerManager
from src.database.manager import DatabaseManager

class WorkerIntegration:
    """Integration layer for WorkerManager with existing bot systems."""
    
    def __init__(self, logger: logging.Logger, db_manager: DatabaseManager):
        self.logger = logger
        self.db = db_manager
        self.worker_manager = WorkerManager(db_manager, logger)
        
    async def initialize(self):
        """Initialize worker manager."""
        try:
            await self.worker_manager.initialize_workers()
            self.logger.info("✅ Worker integration initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize worker integration: {e}")
            return False
    
    async def post_to_destinations(self, slot_id: int, content: str, file_id: str = None) -> Dict[str, Any]:
        """Post content to all destinations of a slot using worker rotation."""
        try:
            # Get slot destinations
            destinations = await self.db.get_slot_destinations(slot_id)
            if not destinations:
                return {'success': False, 'error': 'No destinations found for slot'}
            
            results = {
                'slot_id': slot_id,
                'total_destinations': len(destinations),
                'successful_posts': 0,
                'failed_posts': 0,
                'results': []
            }
            
            for destination in destinations:
                try:
                    chat_id = int(destination['destination_id'])
                    
                    # Post using worker manager
                    success = await self.worker_manager.post_message(
                        chat_id=chat_id,
                        message_text=content,
                        file_id=file_id
                    )
                    
                    if success:
                        results['successful_posts'] += 1
                        results['results'].append({
                            'destination': destination['destination_name'],
                            'status': 'success'
                        })
                    else:
                        results['failed_posts'] += 1
                        results['results'].append({
                            'destination': destination['destination_name'],
                            'status': 'failed',
                            'error': 'Worker posting failed'
                        })
                        
                except Exception as e:
                    results['failed_posts'] += 1
                    results['results'].append({
                        'destination': destination['destination_name'],
                        'status': 'failed',
                        'error': str(e)
                    })
            
            results['success'] = results['successful_posts'] > 0
            return results
            
        except Exception as e:
            self.logger.error(f"Error posting to destinations for slot {slot_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_worker_status(self) -> Dict[str, Any]:
        """Get comprehensive worker status."""
        try:
            health_report = await self.worker_manager.check_worker_health()
            stats = self.worker_manager.get_worker_stats()
            
            return {
                'health': health_report,
                'stats': stats,
                'cooldown_minutes': self.worker_manager.cooldown_minutes
            }
        except Exception as e:
            self.logger.error(f"Error getting worker status: {e}")
            return {'error': str(e)}
    
    async def close(self):
        """Close worker manager."""
        try:
            await self.worker_manager.close_workers()
            self.logger.info("✅ Worker integration closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing worker integration: {e}")

# Global worker integration instance
worker_integration = None

def initialize_worker_integration(logger: logging.Logger, db_manager: DatabaseManager):
    """Initialize the global worker integration."""
    global worker_integration
    worker_integration = WorkerIntegration(logger, db_manager)
    return worker_integration

def get_worker_integration():
    """Get the global worker integration instance."""
    return worker_integration 