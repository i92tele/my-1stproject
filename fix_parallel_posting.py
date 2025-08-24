#!/usr/bin/env python3
"""
Fix Parallel Posting

This script fixes the posting service to use all available workers simultaneously
"""

import asyncio
import sys
import logging
from typing import List, Dict, Any
from src.database.manager import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def create_parallel_posting_service():
    """Create a new parallel posting service that uses all workers simultaneously."""
    try:
        print("🔧 Creating parallel posting service...")
        
        # Read the current posting service
        with open('scheduler/core/posting_service.py', 'r') as f:
            content = f.read()
        
        # Create the new parallel post_ads method
        new_post_ads_method = '''    async def post_ads(self, ad_slots: List[Dict]) -> Dict[str, Any]:
        """Post ads to their destinations using ALL available workers simultaneously.

        Improvements implemented:
        - Parallel posting using all available workers
        - Each ad slot gets assigned to the best available worker
        - Multiple workers post simultaneously for maximum efficiency
        - Automatic restart recovery on first run
        """
        # Perform restart recovery on first run
        if not self.recovery_performed:
            logger.info("🔄 First posting run detected, performing restart recovery...")
            recovery_results = await self.perform_restart_recovery()
            if 'error' in recovery_results:
                logger.warning(f"⚠️ Restart recovery failed, continuing with posting: {recovery_results['error']}")
        
        results = {
            'total_ads': len(ad_slots),
            'successful_posts': 0,
            'failed_posts': 0,
            'errors': []
        }
        
        if not ad_slots:
            logger.info("No ad slots to post")
            return results
        
        # Get all available workers
        available_workers = await self.database.get_available_workers()
        if not available_workers:
            error_msg = "No available workers for posting"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
        
        logger.info(f"🚀 Starting parallel posting with {len(available_workers)} workers for {len(ad_slots)} ad slots")
        
        # Create posting tasks for each ad slot
        posting_tasks = []
        worker_index = 0
        
        for ad_slot in ad_slots:
            slot_id = ad_slot.get('id')
            
            # Check if slot is paused
            if ad_slot.get('is_paused', False):
                pause_reason = ad_slot.get('pause_reason', 'unknown')
                logger.info(f"Slot {slot_id} is paused: {pause_reason}, skipping")
                continue
            
            # Assign worker using round-robin for load balancing
            if available_workers:
                worker_data = available_workers[worker_index % len(available_workers)]
                worker_id = int(worker_data['worker_id'])
                worker = self._get_worker_by_id(worker_id)
                worker_index += 1
                
                if worker:
                    # Create posting task for this slot
                    task = self._post_slot_parallel(ad_slot, worker, results)
                    posting_tasks.append(task)
                    logger.info(f"📝 Created posting task for slot {slot_id} with worker {worker_id}")
                else:
                    error_msg = f"Worker {worker_id} not found for slot {slot_id}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            else:
                error_msg = f"No available workers for slot {slot_id}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        # Execute all posting tasks simultaneously
        if posting_tasks:
            logger.info(f"🔄 Executing {len(posting_tasks)} posting tasks in parallel...")
            await asyncio.gather(*posting_tasks, return_exceptions=True)
        
        logger.info(f"✅ Parallel posting completed: {results['successful_posts']} successful, {results['failed_posts']} failed")
        return results
    
    async def _post_slot_parallel(self, ad_slot: Dict, worker, results: Dict[str, Any]):
        """Post a single ad slot to all its destinations using the assigned worker."""
        slot_id = ad_slot.get('id')
        posted_any = False
        
        try:
            # Load destinations for this slot
            slot_type = ad_slot.get('slot_type', 'user')
            slot_dests = await self.database.get_slot_destinations(slot_id, slot_type)
            
            if not slot_dests:
                logger.debug(f"No destinations for slot {slot_id}, skipping")
                return
            
            logger.info(f"📤 Worker {worker.worker_id} posting slot {slot_id} to {len(slot_dests)} destinations")
            
            for destination in slot_dests:
                try:
                    # Check if worker is still under limit
                    under_limit, usage_info = await self._is_worker_under_limit(worker.worker_id)
                    if not under_limit:
                        logger.warning(f"Worker {worker.worker_id} at limit, skipping remaining destinations for slot {slot_id}")
                        break
                    
                    # Post the ad
                    success = await self._post_single_ad(ad_slot, destination, worker)
                    posted_any = True
                    
                    if success:
                        results['successful_posts'] += 1
                        logger.info(f"✅ Worker {worker.worker_id} successfully posted slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                    else:
                        results['failed_posts'] += 1
                        logger.warning(f"❌ Worker {worker.worker_id} failed to post slot {slot_id} to {destination.get('destination_name', 'Unknown')}")
                    
                    # Record usage
                    try:
                        await self.database.record_worker_post(worker.worker_id, destination.get('destination_id'))
                    except Exception as rec_err:
                        logger.warning(f"Failed to record worker usage: {rec_err}")
                    
                    # Small delay between posts to avoid spam
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    error_msg = f"Error posting slot {slot_id} to destination {destination.get('destination_id')}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed_posts'] += 1
            
            # Update last_sent_at if any posts were made
            if posted_any:
                try:
                    success = await self.database.update_slot_last_sent(slot_id, slot_type)
                    if success:
                        logger.info(f"✅ Updated last_sent_at for slot {slot_id}")
                    else:
                        logger.error(f"❌ Failed to update last_sent_at for slot {slot_id}")
                except Exception as e:
                    logger.error(f"Failed updating last_sent_at for slot {slot_id}: {e}")
            else:
                logger.info(f"ℹ️ No posts made for slot {slot_id}, skipping timestamp update")
                
        except Exception as e:
            error_msg = f"Error processing slot {slot_id}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['failed_posts'] += 1'''
        
        # Replace the old post_ads method with the new one
        import re
        
        # Find the old post_ads method
        old_pattern = r'async def post_ads\(self, ad_slots: List\[Dict\]\) -> Dict\[str, Any\]:.*?return results'
        new_content = re.sub(old_pattern, new_post_ads_method, content, flags=re.DOTALL)
        
        # Add the new _post_slot_parallel method
        if '_post_slot_parallel' not in new_content:
            # Find the end of the class and add the new method before it
            class_end_pattern = r'(\s+)$'
            new_content = re.sub(class_end_pattern, f'\n{new_post_ads_method}\n', new_content)
        
        # Write the updated content back
        with open('scheduler/core/posting_service.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Parallel posting service created successfully!")
        print("🔄 Restart your bot to apply the changes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating parallel posting service: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("PARALLEL POSTING FIX")
    print("=" * 80)
    
    success = asyncio.run(create_parallel_posting_service())
    
    if success:
        print("\n✅ Parallel posting fix completed successfully!")
    else:
        print("\n❌ Parallel posting fix failed!")
    
    sys.exit(0 if success else 1)
