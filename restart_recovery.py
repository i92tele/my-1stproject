#!/usr/bin/env python3
"""
Restart Recovery System
Reconstructs posting timestamps and ban status after bot restarts

This module handles:
1. Timestamp reconstruction for posting schedules
2. Ban status recovery and validation
3. Posting history analysis for recovery
4. Worker health assessment after restart
5. Destination health validation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from src.database.manager import DatabaseManager
import sqlite3

logger = logging.getLogger(__name__)

class RestartRecovery:
    """Handles system recovery after bot restarts."""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.recovery_data = {}
        
    async def perform_full_recovery(self) -> Dict[str, Any]:
        """Perform complete system recovery after restart."""
        logger.info("🔄 Starting full system recovery after restart...")
        
        recovery_results = {
            'timestamp_reconstruction': {},
            'ban_status_recovery': {},
            'posting_history_analysis': {},
            'worker_health_assessment': {},
            'destination_health_validation': {},
            'recovery_summary': {}
        }
        
        try:
            # Step 1: Reconstruct posting timestamps
            recovery_results['timestamp_reconstruction'] = await self._reconstruct_posting_timestamps()
            
            # Step 2: Recover ban status
            recovery_results['ban_status_recovery'] = await self._recover_ban_status()
            
            # Step 3: Analyze posting history
            recovery_results['posting_history_analysis'] = await self._analyze_posting_history()
            
            # Step 4: Assess worker health
            recovery_results['worker_health_assessment'] = await self._assess_worker_health()
            
            # Step 5: Validate destination health
            recovery_results['destination_health_validation'] = await self._validate_destination_health()
            
            # Generate recovery summary
            recovery_results['recovery_summary'] = self._generate_recovery_summary(recovery_results)
            
            logger.info("✅ Full system recovery completed successfully")
            return recovery_results
            
        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}")
            return {'error': str(e)}
    
    async def _reconstruct_posting_timestamps(self) -> Dict[str, Any]:
        """Reconstruct posting timestamps for active ad slots."""
        logger.info("🕐 Reconstructing posting timestamps...")
        
        try:
            # Get all active ad slots
            active_slots = await self.db.get_active_ads_to_send()
            
            reconstructed_slots = []
            skipped_slots = []
            updated_slots = []
            
            for slot in active_slots:
                slot_id = slot.get('id')
                slot_type = slot.get('slot_type', 'user')
                interval_minutes = slot.get('interval_minutes', 60)
                last_sent_at = slot.get('last_sent_at')
                
                # Calculate when this slot should post next
                next_post_time = await self._calculate_next_post_time(
                    slot_id, slot_type, interval_minutes, last_sent_at
                )
                
                if next_post_time is None:
                    # Slot is due for posting, don't update timestamp
                    logger.info(f"Slot {slot_id}: Due for posting, skipping timestamp update")
                    skipped_slots.append({
                        'slot_id': slot_id,
                        'slot_type': slot_type,
                        'reason': 'due_for_posting',
                        'next_post_time': None
                    })
                    continue
                elif next_post_time:
                    # Only update if the slot is not due yet
                    success = await self._update_slot_timestamp(slot_id, slot_type, next_post_time)
                    
                    if success:
                        updated_slots.append({
                            'slot_id': slot_id,
                            'slot_type': slot_type,
                            'old_timestamp': last_sent_at,
                            'new_timestamp': next_post_time,
                            'recovery_method': 'timestamp_reconstruction'
                        })
                        reconstructed_slots.append(slot_id)
                    else:
                        logger.warning(f"Failed to update timestamp for slot {slot_id}")
                else:
                    logger.warning(f"Could not calculate next post time for slot {slot_id}")
            
            logger.info(f"🕐 Reconstructed {len(reconstructed_slots)} slots, updated {len(updated_slots)} in database, skipped {len(skipped_slots)}")
            
            return {
                'reconstructed_slots': reconstructed_slots,
                'updated_slots': updated_slots,
                'skipped_slots': skipped_slots,
                'total_processed': len(active_slots)
            }
            
        except Exception as e:
            logger.error(f"Error reconstructing timestamps: {e}")
            return {'error': str(e)}
    
    async def _calculate_next_post_time(self, slot_id: int, slot_type: str, 
                                      interval_minutes: int, last_sent_at: str) -> Optional[str]:
        """Calculate when a slot should post next based on history and restart recovery."""
        try:
            current_time = datetime.now()
            
            # If we have a last_sent_at timestamp, use it as the base
            if last_sent_at:
                try:
                    last_sent_time = datetime.fromisoformat(last_sent_at.replace('Z', '+00:00'))
                    
                    # Calculate how much time has passed since last sent
                    time_since_last = current_time - last_sent_time
                    minutes_since_last = time_since_last.total_seconds() / 60
                    
                    # If enough time has passed (more than interval), don't update timestamp
                    # Let the scheduler post it naturally
                    if minutes_since_last >= interval_minutes:
                        logger.info(f"Slot {slot_id}: {minutes_since_last:.1f} minutes since last post, due for posting - skipping timestamp update")
                        return None  # Don't update timestamp, let scheduler post it
                    else:
                        # Calculate when it should post next
                        minutes_until_next = interval_minutes - minutes_since_last
                        next_time = last_sent_time + timedelta(minutes=interval_minutes)
                        logger.info(f"Slot {slot_id}: Will post in {minutes_until_next:.1f} minutes at {next_time}")
                        return next_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                except Exception as e:
                    logger.warning(f"Error parsing last_sent_at for slot {slot_id}: {e}")
            
            # Fallback: Get recent posting history for this slot
            history = await self.db.get_posting_history(limit=10)
            
            if not history:
                # No history available, use current time + interval
                next_time = current_time + timedelta(minutes=interval_minutes)
                logger.info(f"Slot {slot_id}: No history, will post in {interval_minutes} minutes")
                return next_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Find the most recent successful post
            recent_posts = [h for h in history if h['success']]
            
            if not recent_posts:
                # No successful posts, use current time + interval
                next_time = current_time + timedelta(minutes=interval_minutes)
                logger.info(f"Slot {slot_id}: No successful posts in history, will post in {interval_minutes} minutes")
                return next_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get the most recent post time
            latest_post = max(recent_posts, key=lambda x: x['posted_at'])
            latest_time = datetime.fromisoformat(latest_post['posted_at'].replace('Z', '+00:00'))
            
            # Calculate next post time
            next_time = latest_time + timedelta(minutes=interval_minutes)
            
            # If next time is in the past, use current time + interval
            if next_time < current_time:
                next_time = current_time + timedelta(minutes=interval_minutes)
                logger.info(f"Slot {slot_id}: Next time was in past, will post in {interval_minutes} minutes")
            else:
                logger.info(f"Slot {slot_id}: Will post at {next_time} based on history")
            
            return next_time.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            logger.error(f"Error calculating next post time for slot {slot_id}: {e}")
            return None
    
    async def _update_slot_timestamp(self, slot_id: int, slot_type: str, timestamp: str) -> bool:
        """Update the last_sent_at timestamp for a slot in the database."""
        try:
            if slot_type == 'admin':
                # Update admin slot timestamp
                conn = sqlite3.connect(self.db.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE admin_ad_slots 
                    SET last_sent_at = ?
                    WHERE id = ?
                ''', (timestamp, slot_id))
                conn.commit()
                conn.close()
            else:
                # Update user slot timestamp
                conn = sqlite3.connect(self.db.db_path, timeout=15)
                conn.execute("PRAGMA busy_timeout=15000;")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ad_slots 
                    SET last_sent_at = ?
                    WHERE id = ?
                ''', (timestamp, slot_id))
                conn.commit()
                conn.close()
            
            logger.info(f"✅ Updated {slot_type} slot {slot_id} timestamp to {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating slot {slot_id} timestamp: {e}")
            return False
    
    async def _recover_ban_status(self) -> Dict[str, Any]:
        """Recover and validate worker ban status."""
        logger.info("🚫 Recovering worker ban status...")
        
        try:
            # Get all active bans
            active_bans = await self.db.get_worker_bans(active_only=True)
            
            recovered_bans = []
            expired_bans = []
            
            for ban in active_bans:
                banned_at = datetime.fromisoformat(ban['banned_at'].replace('Z', '+00:00'))
                estimated_unban = ban.get('estimated_unban_time')
                
                # Check if ban has expired
                if estimated_unban:
                    try:
                        unban_time = datetime.fromisoformat(estimated_unban.replace('Z', '+00:00'))
                        if datetime.now() > unban_time:
                            # Ban has expired, clear it
                            await self.db.clear_worker_ban(ban['worker_id'], ban['destination_id'])
                            expired_bans.append({
                                'worker_id': ban['worker_id'],
                                'destination_id': ban['destination_id'],
                                'ban_type': ban['ban_type'],
                                'expired_at': unban_time.strftime('%Y-%m-%d %H:%M:%S')
                            })
                            continue
                    except Exception as e:
                        logger.warning(f"Error parsing unban time for ban {ban['id']}: {e}")
                
                # Ban is still active
                recovered_bans.append({
                    'worker_id': ban['worker_id'],
                    'destination_id': ban['destination_id'],
                    'ban_type': ban['ban_type'],
                    'banned_at': ban['banned_at'],
                    'estimated_unban': estimated_unban,
                    'recovery_method': 'ban_status_recovery'
                })
            
            logger.info(f"🚫 Recovered {len(recovered_bans)} active bans, cleared {len(expired_bans)} expired bans")
            
            return {
                'recovered_bans': recovered_bans,
                'expired_bans': expired_bans,
                'total_processed': len(active_bans)
            }
            
        except Exception as e:
            logger.error(f"Error recovering ban status: {e}")
            return {'error': str(e)}
    
    async def _analyze_posting_history(self) -> Dict[str, Any]:
        """Analyze posting history for recovery insights."""
        logger.info("📊 Analyzing posting history for recovery...")
        
        try:
            # Get recent posting activity
            recent_activity = await self.db.get_recent_posting_activity(hours=24)
            
            # Analyze posting patterns
            history = await self.db.get_posting_history(limit=100)
            
            # Group by worker
            worker_stats = {}
            for record in history:
                worker_id = record['worker_id']
                if worker_id not in worker_stats:
                    worker_stats[worker_id] = {
                        'total_posts': 0,
                        'successful_posts': 0,
                        'failed_posts': 0,
                        'ban_detections': 0,
                        'last_activity': None
                    }
                
                worker_stats[worker_id]['total_posts'] += 1
                if record['success']:
                    worker_stats[worker_id]['successful_posts'] += 1
                else:
                    worker_stats[worker_id]['failed_posts'] += 1
                
                if record['ban_detected']:
                    worker_stats[worker_id]['ban_detections'] += 1
                
                # Track last activity
                post_time = datetime.fromisoformat(record['posted_at'].replace('Z', '+00:00'))
                if (worker_stats[worker_id]['last_activity'] is None or 
                    post_time > worker_stats[worker_id]['last_activity']):
                    worker_stats[worker_id]['last_activity'] = post_time
            
            # Calculate success rates
            for worker_id, stats in worker_stats.items():
                if stats['total_posts'] > 0:
                    stats['success_rate'] = (stats['successful_posts'] / stats['total_posts']) * 100
                else:
                    stats['success_rate'] = 0
            
            logger.info(f"📊 Analyzed {len(history)} posting records for {len(worker_stats)} workers")
            
            return {
                'recent_activity': recent_activity,
                'worker_stats': worker_stats,
                'total_records_analyzed': len(history)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing posting history: {e}")
            return {'error': str(e)}
    
    async def _assess_worker_health(self) -> Dict[str, Any]:
        """Assess worker health after restart."""
        logger.info("🏥 Assessing worker health...")
        
        try:
            # Get all workers with their ban status
            all_bans = await self.db.get_worker_bans(active_only=True)
            
            # Group bans by worker
            worker_bans = {}
            for ban in all_bans:
                worker_id = ban['worker_id']
                if worker_id not in worker_bans:
                    worker_bans[worker_id] = []
                worker_bans[worker_id].append(ban)
            
            # Assess each worker's health
            worker_health = {}
            for worker_id, bans in worker_bans.items():
                health_score = 100  # Start with perfect health
                
                # Deduct points for bans
                health_score -= len(bans) * 20  # 20 points per ban
                
                # Check ban types
                ban_types = [ban['ban_type'] for ban in bans]
                if 'permission_denied' in ban_types:
                    health_score -= 30  # Severe penalty for permission denied
                if 'rate_limit' in ban_types:
                    health_score -= 15  # Moderate penalty for rate limits
                
                # Ensure health score doesn't go below 0
                health_score = max(0, health_score)
                
                worker_health[worker_id] = {
                    'health_score': health_score,
                    'ban_count': len(bans),
                    'ban_types': ban_types,
                    'status': 'healthy' if health_score >= 70 else 'warning' if health_score >= 40 else 'critical'
                }
            
            logger.info(f"🏥 Assessed health for {len(worker_health)} workers")
            
            return {
                'worker_health': worker_health,
                'total_workers_assessed': len(worker_health)
            }
            
        except Exception as e:
            logger.error(f"Error assessing worker health: {e}")
            return {'error': str(e)}
    
    async def _validate_destination_health(self) -> Dict[str, Any]:
        """Validate destination health after restart."""
        logger.info("🎯 Validating destination health...")
        
        try:
            # Get destination health summary
            health_summary = await self.db.get_destination_health_summary()
            
            # Get problematic destinations
            problematic = await self.db.get_problematic_destinations(min_failures=2)
            
            # Validate each destination
            destination_validation = {}
            for dest in health_summary.get('worst_destinations', []):
                dest_id = dest['destination_id']
                health_data = await self.db.get_destination_health(dest_id)
                
                validation_status = 'healthy'
                if health_data['success_rate'] < 30:
                    validation_status = 'critical'
                elif health_data['success_rate'] < 60:
                    validation_status = 'warning'
                
                destination_validation[dest_id] = {
                    'success_rate': health_data['success_rate'],
                    'total_attempts': health_data['total_attempts'],
                    'validation_status': validation_status,
                    'recommendation': self._get_destination_recommendation(health_data)
                }
            
            logger.info(f"🎯 Validated {len(destination_validation)} destinations")
            
            return {
                'health_summary': health_summary,
                'problematic_destinations': problematic,
                'destination_validation': destination_validation
            }
            
        except Exception as e:
            logger.error(f"Error validating destination health: {e}")
            return {'error': str(e)}
    
    def _get_destination_recommendation(self, health_data: Dict[str, Any]) -> str:
        """Get recommendation for destination based on health data."""
        success_rate = health_data.get('success_rate', 100)
        total_attempts = health_data.get('total_attempts', 0)
        
        if total_attempts < 3:
            return "insufficient_data"
        elif success_rate < 30:
            return "consider_removal"
        elif success_rate < 60:
            return "monitor_closely"
        else:
            return "healthy"
    
    def _generate_recovery_summary(self, recovery_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the recovery process."""
        summary = {
            'recovery_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_status': 'success',
            'components_recovered': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check each component
        if 'timestamp_reconstruction' in recovery_results:
            ts_data = recovery_results['timestamp_reconstruction']
            if 'error' not in ts_data:
                summary['components_recovered'].append('timestamp_reconstruction')
                if ts_data.get('skipped_slots'):
                    summary['warnings'].append(f"{len(ts_data['skipped_slots'])} slots skipped due to insufficient history")
        
        if 'ban_status_recovery' in recovery_results:
            ban_data = recovery_results['ban_status_recovery']
            if 'error' not in ban_data:
                summary['components_recovered'].append('ban_status_recovery')
                if ban_data.get('expired_bans'):
                    summary['recommendations'].append(f"{len(ban_data['expired_bans'])} expired bans were cleared")
        
        if 'posting_history_analysis' in recovery_results:
            ph_data = recovery_results['posting_history_analysis']
            if 'error' not in ph_data:
                summary['components_recovered'].append('posting_history_analysis')
        
        if 'worker_health_assessment' in recovery_results:
            wh_data = recovery_results['worker_health_assessment']
            if 'error' not in wh_data:
                summary['components_recovered'].append('worker_health_assessment')
                
                # Check for critical worker health
                critical_workers = [wid for wid, health in wh_data.get('worker_health', {}).items() 
                                  if health['status'] == 'critical']
                if critical_workers:
                    summary['warnings'].append(f"{len(critical_workers)} workers have critical health status")
        
        if 'destination_health_validation' in recovery_results:
            dh_data = recovery_results['destination_health_validation']
            if 'error' not in dh_data:
                summary['components_recovered'].append('destination_health_validation')
                
                # Check for problematic destinations
                problematic = dh_data.get('problematic_destinations', [])
                if problematic:
                    summary['warnings'].append(f"{len(problematic)} destinations have poor performance")
        
        # Set overall status
        if len(summary['warnings']) > 3:
            summary['overall_status'] = 'warning'
        elif len(summary['components_recovered']) < 5:
            summary['overall_status'] = 'partial'
        
        return summary
    
    async def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery status."""
        return {
            'recovery_data': self.recovery_data,
            'last_recovery': getattr(self, 'last_recovery_time', None),
            'system_status': 'recovered' if self.recovery_data else 'pending'
        }
